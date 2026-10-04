import re

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import Client

from lety.models import AuditLog
from osoby.models import Osoba
from provoz.models import EmailRezim, Nastaveni

pytestmark = pytest.mark.django_db

HESLO = "Kluzak-Blanik-1956"


@pytest.fixture(autouse=True)
def cisty_cache():
    cache.clear()


@pytest.fixture
def klient():
    """Klient, který vynucuje CSRF jako skutečný prohlížeč."""
    c = Client(enforce_csrf_checks=True)
    c.get("/api/ucet/ja")
    return c


def post(klient, url, data):
    token = klient.cookies["csrftoken"].value
    return klient.post(url, data, content_type="application/json", HTTP_X_CSRFTOKEN=token)


@pytest.fixture
def pilot(db):
    return Osoba.objects.create_user("pilot@example.com", HESLO, jmeno="Adam", prijmeni="Pilot")


@pytest.fixture
def admin(db):
    return Osoba.objects.create_superuser(
        "admin@example.com", HESLO, jmeno="Tomáš", prijmeni="Admin"
    )


def povolit_emaily(*adresy):
    nastaveni = Nastaveni.aktualni()
    nastaveni.email_rezim = EmailRezim.POVOLENE
    nastaveni.povolene_adresy = "\n".join(adresy)
    nastaveni.save()


# --- režim odesílání ---------------------------------------------------------


def test_vychozi_rezim_nic_neposila(db):
    assert not Nastaveni.aktualni().smi_odeslat("kdokoli@example.com")


def test_povolene_adresy_s_hvezdickou(db):
    povolit_emaily("tomas@example.com", "tomas+*@example.com")
    nastaveni = Nastaveni.aktualni()
    assert nastaveni.smi_odeslat("Tomas@Example.com")
    assert nastaveni.smi_odeslat("tomas+pilot@example.com")
    assert not nastaveni.smi_odeslat("jiny@example.com")


# --- přihlášení --------------------------------------------------------------


def test_nepřihlaseny(klient):
    data = klient.get("/api/ucet/ja").json()
    assert data["prihlasen"] is False
    assert data["testovaci_provoz"] is True


def test_prihlaseni_a_odhlaseni(klient, pilot):
    odpoved = post(klient, "/api/ucet/prihlasit", {"email": "Pilot@example.com", "heslo": HESLO})
    assert odpoved.status_code == 200
    data = odpoved.json()
    assert data["prihlasen"] and data["jmeno"] == "Adam"
    assert data["role"] == {"admin": False, "casomeric": False, "ucetni": False}

    assert post(klient, "/api/ucet/odhlasit", {}).status_code == 200
    assert klient.get("/api/ucet/ja").json()["prihlasen"] is False


def test_prihlaseni_bez_csrf_neprojde(pilot):
    klient = Client(enforce_csrf_checks=True)
    odpoved = klient.post(
        "/api/ucet/prihlasit",
        {"email": "pilot@example.com", "heslo": HESLO},
        content_type="application/json",
    )
    assert odpoved.status_code == 403


def test_spatne_heslo_a_omezeni_pokusu(klient, pilot):
    for _ in range(5):
        odpoved = post(klient, "/api/ucet/prihlasit", {"email": "pilot@example.com", "heslo": "x"})
        assert odpoved.status_code == 401
    # Šestý pokus je zablokovaný, i se správným heslem.
    odpoved = post(klient, "/api/ucet/prihlasit", {"email": "pilot@example.com", "heslo": HESLO})
    assert odpoved.status_code == 429


def test_osoba_bez_hesla_se_neprihlasi(klient, db):
    Osoba.objects.create_user("bez@example.com", jmeno="Eva", prijmeni="Bez")
    odpoved = post(klient, "/api/ucet/prihlasit", {"email": "bez@example.com", "heslo": ""})
    assert odpoved.status_code == 401


# --- zapomenuté heslo a nastavení hesla ---------------------------------------


def test_zapomenute_heslo_bez_povoleni_neodejde(klient, pilot):
    odpoved = post(klient, "/api/ucet/zapomenute-heslo", {"email": "pilot@example.com"})
    assert odpoved.status_code == 200
    assert mail.outbox == []


def test_zapomenute_heslo_neprozradi_neexistujici_ucet(klient, db):
    povolit_emaily("*")
    odpoved = post(klient, "/api/ucet/zapomenute-heslo", {"email": "nikdo@example.com"})
    assert odpoved.status_code == 200
    assert "Pokud je e-mail" in odpoved.json()["zprava"]
    assert mail.outbox == []


def test_nastaveni_hesla_z_odkazu(klient, pilot):
    povolit_emaily("pilot@example.com")
    post(klient, "/api/ucet/zapomenute-heslo", {"email": "pilot@example.com"})
    assert len(mail.outbox) == 1
    uid, token = re.search(r"/nastavit-heslo/([^/]+)/(\S+)", mail.outbox[0].body).groups()

    assert klient.get(f"/api/ucet/nastavit-heslo/{uid}/{token}").json()["zprava"] == (
        "pilot@example.com"
    )
    slabe = post(klient, "/api/ucet/nastavit-heslo", {"uid": uid, "token": token, "heslo": "123"})
    assert slabe.status_code == 400

    nove = "Vlecna-Zlin-226"
    odpoved = post(klient, "/api/ucet/nastavit-heslo", {"uid": uid, "token": token, "heslo": nove})
    assert odpoved.status_code == 200 and odpoved.json()["prihlasen"]
    pilot.refresh_from_db()
    assert pilot.check_password(nove)
    # Odkaz po použití přestane platit.
    assert klient.get(f"/api/ucet/nastavit-heslo/{uid}/{token}").status_code == 400


def test_neplatny_odkaz(klient, db):
    assert klient.get("/api/ucet/nastavit-heslo/MQ/neplatny-token").status_code == 400


# --- pozvánky a „Přihlásit se jako“ (administrace) -----------------------------


def test_pozvanky_respektuji_rezim(client, admin, pilot):
    externi = Osoba.objects.create_user(None, jmeno="Karel", prijmeni="Externí", externi=True)
    client.force_login(admin)
    akce = {"action": "poslat_pozvanky", "_selected_action": [pilot.pk, externi.pk]}

    client.post("/admin/osoby/osoba/", akce)
    assert mail.outbox == []  # režim „vypnuto“

    povolit_emaily("pilot@example.com")
    client.post("/admin/osoby/osoba/", akce)
    assert len(mail.outbox) == 1
    assert "/nastavit-heslo/" in mail.outbox[0].body
    pilot.refresh_from_db()
    assert pilot.pozvanka_odeslana is not None
    assert AuditLog.objects.filter(akce="pozvanka", objekt_id=pilot.pk).exists()


def test_prihlasit_se_jako_a_vratit_se(admin, pilot):
    klient = Client()
    klient.force_login(admin)
    odpoved = klient.post(
        "/admin/osoby/osoba/", {"action": "prihlasit_jako", "_selected_action": [pilot.pk]}
    )
    assert odpoved.status_code == 302 and odpoved.url == "/"

    ja = klient.get("/api/ucet/ja").json()
    assert ja["id"] == pilot.pk
    assert ja["role"]["admin"] is False
    assert ja["zastupce"]["id"] == admin.pk
    # Jako pilot se do administrace nedostane.
    assert klient.get("/admin/").status_code == 302

    assert klient.post("/api/ucet/vratit-se").json()["id"] == admin.pk
    assert klient.get("/api/ucet/ja").json()["zastupce"] is None
    akce = list(AuditLog.objects.values_list("akce", flat=True).order_by("id"))
    assert akce == ["prihlaseni_jako", "prihlaseni_jako_konec"]


def test_neaktivni_osobu_nejde_prevzit(client, admin, db):
    neaktivni = Osoba.objects.create_user(
        "pryc@example.com", HESLO, jmeno="Libor", prijmeni="Pryč", is_active=False
    )
    client.force_login(admin)
    client.post(
        "/admin/osoby/osoba/", {"action": "prihlasit_jako", "_selected_action": [neaktivni.pk]}
    )
    assert client.get("/api/ucet/ja").json()["id"] == admin.pk


def test_nastaveni_v_administraci(client, admin):
    client.force_login(admin)
    odpoved = client.get("/admin/provoz/nastaveni/")
    assert odpoved.status_code == 302
    assert client.get(odpoved.url).status_code == 200
