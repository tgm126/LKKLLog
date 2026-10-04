from datetime import timedelta

import pytest
from django.utils import timezone

from lety.models import AuditLog, Let, Letadlo, Letiste, Osnova, StavLetu, Ucel, Uloha
from osoby.models import Kategorie, Osoba

pytestmark = pytest.mark.django_db


def osoba(prijmeni, **kw):
    return Osoba.objects.create_user(None, jmeno="Test", prijmeni=prijmeni, **kw)


@pytest.fixture
def svet(db):
    """Malý testovací aeroklub."""
    s = type("Svet", (), {})()
    s.lkkl = Letiste.objects.create(icao="LKKL", nazev="Kladno", domovske=True)
    s.teren = Letiste.objects.create(nazev="Mimo letiště", teren=True)
    s.motor = Letadlo.objects.create(
        imatrikulace="OK-TCS",
        typ="Cessna",
        kategorie=Kategorie.MOTOR,
        pocet_mist=4,
        max_doba_min=300,
    )
    s.dvoumistne = Letadlo.objects.create(
        imatrikulace="OK-TVA", typ="Z-226", kategorie=Kategorie.MOTOR, pocet_mist=2
    )
    s.kluzak = Letadlo.objects.create(
        imatrikulace="OK-T101", typ="L-13", kategorie=Kategorie.KLUZAK, pocet_mist=2
    )
    s.pilot = osoba("Pilot")
    s.zak = osoba("Žák")
    s.instruktor = osoba("Instruktor")
    s.cizi_pilot = osoba("Cizí")
    s.casomeric = osoba("Časoměřič", role_casomeric=True)
    s.externi = osoba("Externí", externi=True)
    osnova = Osnova.objects.create(kategorie=Kategorie.MOTOR, nazev="Základní výcvik")
    s.uloha = Uloha.objects.create(osnova=osnova, kod="M2", nazev="Okruhy", ucely=[Ucel.VYCVIK])
    return s


@pytest.fixture
def jako(client):
    def prihlasit(o):
        client.force_login(o)
        return client

    return prihlasit


def post(klient, url, data=None):
    return klient.post(url, data or {}, content_type="application/json")


def normalni(svet, **kw):
    data = {
        "letadlo_id": svet.motor.pk,
        "ucel": Ucel.NORMALNI,
        "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}],
    }
    data.update(kw)
    return data


# --- přístup a číselníky ---------------------------------------------------------


def test_bez_prihlaseni_nic(client, svet):
    assert client.get("/api/prehled").status_code == 401
    assert client.get("/api/ciselniky").status_code == 401


def test_ciselniky_bez_telefonu(jako, svet):
    svet.pilot.telefon = "+420000000001"
    svet.pilot.save()
    data = jako(svet.pilot).get("/api/ciselniky").json()
    assert {a["imatrikulace"] for a in data["letadla"]} == {"OK-TCS", "OK-TVA", "OK-T101"}
    assert "telefon" not in data["osoby"][0]
    assert "+420000000001" not in str(data)
    assert data["osnovy"][0]["ulohy"][0]["kod"] == "M2"


# --- založení letu a pravidla -------------------------------------------------------


def test_vzlet_ted(jako, svet):
    odpoved = post(jako(svet.pilot), "/api/lety", normalni(svet))
    assert odpoved.status_code == 200, odpoved.json()
    let = odpoved.json()
    assert let["stav"] == StavLetu.VE_VZDUCHU
    assert let["platce"] == "Test Pilot"
    assert let["misto_vzletu"] == "LKKL"
    assert let["muze_ovladat"] is True
    assert AuditLog.objects.filter(akce="zalozeni", objekt_id=let["id"]).exists()


def test_vycvik_bez_zaka_neprojde(jako, svet):
    data = normalni(svet, ucel=Ucel.VYCVIK)
    odpoved = post(jako(svet.pilot), "/api/lety", data)
    assert odpoved.status_code == 400
    assert "Žák" in odpoved.json()["detail"]


def test_vycvik_plati_zak(jako, svet):
    data = normalni(
        svet,
        ucel=Ucel.VYCVIK,
        uloha_id=svet.uloha.pk,
        posadka=[
            {"osoba_id": svet.instruktor.pk, "funkce": "pic"},
            {"osoba_id": svet.zak.pk, "funkce": "zak"},
        ],
    )
    let = post(jako(svet.instruktor), "/api/lety", data).json()
    assert let["platce"] == "Test Žák"
    assert let["uloha"] == "M2 – Okruhy"


def test_solo_dozor_nezabira_misto(jako, svet):
    data = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        ucel=Ucel.VYCVIK_SOLO,
        pocet_hostu=1,
        posadka=[
            {"osoba_id": svet.zak.pk, "funkce": "pic"},
            {"osoba_id": svet.instruktor.pk, "funkce": "dozor"},
        ],
    )
    let = post(jako(svet.zak), "/api/lety", data).json()
    assert let["platce"] == "Test Žák"


def test_prilis_mnoho_lidi(jako, svet):
    data = normalni(svet, letadlo_id=svet.dvoumistne.pk, pocet_hostu=2)
    odpoved = post(jako(svet.pilot), "/api/lety", data)
    assert odpoved.status_code == 400
    assert "2 míst" in odpoved.json()["detail"]


def test_externi_jen_jako_pic_pri_prezkouseni(jako, svet):
    prezkouseni = normalni(
        svet,
        ucel=Ucel.PREZKOUSENI,
        posadka=[
            {"osoba_id": svet.externi.pk, "funkce": "pic"},
            {"osoba_id": svet.pilot.pk, "funkce": "prezkouseny"},
        ],
    )
    let = post(jako(svet.pilot), "/api/lety", prezkouseni).json()
    assert let["platce"] == "Test Pilot"

    normalni_let = normalni(
        svet,
        letadlo_id=svet.dvoumistne.pk,
        posadka=[{"osoba_id": svet.externi.pk, "funkce": "pic"}],
    )
    assert post(jako(svet.pilot), "/api/lety", normalni_let).status_code == 400


def test_plati_aeroklub(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet, plati_aeroklub=True)).json()
    assert let["plati_aeroklub"] and let["platce"] is None


def test_uloha_musi_sedet(jako, svet):
    # Úloha je pro výcvik, ne pro normální let.
    odpoved = post(jako(svet.pilot), "/api/lety", normalni(svet, uloha_id=svet.uloha.pk))
    assert odpoved.status_code == 400


def test_kluzak_potrebuje_zpusob_vzletu(jako, svet):
    data = normalni(svet, letadlo_id=svet.kluzak.pk)
    assert post(jako(svet.pilot), "/api/lety", data).status_code == 400
    data["zpusob_vzletu"] = "vlek"
    assert post(jako(svet.pilot), "/api/lety", data).status_code == 400
    data["zpusob_vzletu"] = "navijak"
    assert post(jako(svet.pilot), "/api/lety", data).json()["zpusob_vzletu"] == "navijak"


def test_letadlo_ve_vzduchu_nejde_zalozit_znovu(jako, svet):
    prvni = post(jako(svet.pilot), "/api/lety", normalni(svet)).json()
    data = normalni(svet, posadka=[{"osoba_id": svet.casomeric.pk, "funkce": "pic"}])
    odpoved = post(jako(svet.casomeric), "/api/lety", data)
    assert odpoved.status_code == 409
    assert odpoved.json()["kod"] == "letadlo_obsazeno"
    assert odpoved.json()["let_id"] == prvni["id"]


# --- vzlet, přistání, souběh -------------------------------------------------------


def test_pripraveny_let_a_dvojity_vzlet(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet, akce="pripravit")).json()
    assert let["stav"] == StavLetu.PRIPRAVEN and let["cas_vzletu"] is None

    assert post(jako(svet.pilot), f"/api/lety/{let['id']}/vzlet").status_code == 200
    druhy = post(jako(svet.casomeric), f"/api/lety/{let['id']}/vzlet")
    assert druhy.status_code == 409
    assert druhy.json()["kod"] == "uz_zapsano"
    assert "Test Pilot" in druhy.json()["detail"]


def _ve_vzduchu(svet, minut=20):
    let = Let.objects.create(
        letadlo=svet.motor,
        ucel=Ucel.NORMALNI,
        misto_vzletu=svet.lkkl,
        platce=svet.pilot,
        zalozil=svet.pilot,
        stav=StavLetu.VE_VZDUCHU,
        cas_vzletu=timezone.now().replace(microsecond=0) - timedelta(minutes=minut),
    )
    let.posadka.create(osoba=svet.pilot, funkce="pic")
    return let


def test_pristani_a_dvojity_stisk(jako, svet):
    let = _ve_vzduchu(svet)
    odpoved = post(jako(svet.casomeric), f"/api/lety/{let.pk}/pristani", {"pocet_tg": 3})
    assert odpoved.status_code == 200
    data = odpoved.json()
    assert data["stav"] == StavLetu.UKONCEN
    assert data["doba_min"] == 20 and data["pocet_tg"] == 3
    assert data["misto_pristani"] == "LKKL"

    druhy = post(jako(svet.pilot), f"/api/lety/{let.pk}/pristani")
    assert druhy.status_code == 409
    assert "Test Časoměřič" in druhy.json()["detail"]


def test_cizi_pilot_neovlada_cizi_let(jako, svet):
    let = _ve_vzduchu(svet)
    assert post(jako(svet.cizi_pilot), f"/api/lety/{let.pk}/pristani").status_code == 403
    prehled = jako(svet.cizi_pilot).get("/api/prehled").json()
    assert prehled["lety"][0]["muze_ovladat"] is False


def test_kratky_let_vyzaduje_volbu(jako, svet):
    let = _ve_vzduchu(svet, minut=0)
    klient = jako(svet.pilot)
    odpoved = post(klient, f"/api/lety/{let.pk}/pristani")
    assert odpoved.status_code == 409 and odpoved.json()["kod"] == "kratky_let"
    odpoved = post(klient, f"/api/lety/{let.pk}/pristani", {"kratky_let": "start_bez_doby"})
    assert odpoved.status_code == 200
    assert odpoved.json()["doba_uctovana_min"] == 0


def test_dopsat_probehly_let(jako, svet):
    ted = timezone.now().replace(microsecond=0)
    data = normalni(
        svet,
        akce="dopsat",
        cas_vzletu=(ted - timedelta(hours=2)).isoformat(),
        cas_pristani=(ted - timedelta(hours=1)).isoformat(),
        misto_pristani_id=svet.teren.pk,
        pocet_tg=2,
    )
    let = post(jako(svet.pilot), "/api/lety", data).json()
    assert let["stav"] == StavLetu.UKONCEN
    assert let["doba_min"] == 60
    assert let["dodatecne"] is True
    assert let["misto_pristani"] == "Mimo letiště"


def test_vzlet_v_budoucnu_neprojde(jako, svet):
    data = normalni(svet, cas_vzletu=(timezone.now() + timedelta(hours=1)).isoformat())
    assert post(jako(svet.pilot), "/api/lety", data).status_code == 400


def test_zruseni(jako, svet):
    let = post(jako(svet.pilot), "/api/lety", normalni(svet, akce="pripravit")).json()
    klient = jako(svet.pilot)
    assert post(klient, f"/api/lety/{let['id']}/zrusit", {"duvod": "nesmysl"}).status_code == 400
    data = post(klient, f"/api/lety/{let['id']}/zrusit", {"duvod": "omyl"}).json()
    assert data["stav"] == StavLetu.ZRUSEN and data["duvod_zruseni"] == "omyl"


def test_prehled_dne(jako, svet):
    _ve_vzduchu(svet)
    data = jako(svet.pilot).get("/api/prehled").json()
    assert len(data["lety"]) == 1
    assert data["konec_soumraku"] > data["zapad_slunce"]
    vcera = (timezone.now() - timedelta(days=1)).date().isoformat()
    assert jako(svet.pilot).get(f"/api/prehled?den={vcera}").json()["lety"] == []
