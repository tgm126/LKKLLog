import json
from datetime import UTC, datetime, time, timedelta

import pytest
from django.core import mail
from django.utils import timezone
from pywebpush import WebPushException

from lety.models import AuditLog, Let, StavLetu, Ucel, Upozorneni
from lety.slunce import slunce
from lety.upozorneni import kontrola
from osoby.models import Osoba
from provoz import push
from provoz.models import EmailRezim, Nastaveni, PushOdber

from .pomocne import post

pytestmark = pytest.mark.django_db


@pytest.fixture
def odeslane(monkeypatch):
    """Zachytí push notifikace místo odeslání do push služby."""
    zpravy = []

    def webpush(subscription_info, data, **kw):
        zpravy.append((subscription_info["endpoint"], json.loads(data)))

    monkeypatch.setattr(push, "webpush", webpush)
    return zpravy


@pytest.fixture
def lide(svet):
    """Pilot a časoměřič s e-mailem; e-maily povolené jen na example.com."""
    nastaveni = Nastaveni.aktualni()
    nastaveni.email_rezim = EmailRezim.POVOLENE
    nastaveni.povolene_adresy = "*@example.com"
    nastaveni.save()
    for o, adresa in ((svet.pilot, "pilot@example.com"), (svet.casomeric, "cas@example.com")):
        o.email = adresa
        o.save()
    PushOdber.objects.create(
        osoba=svet.pilot, endpoint="https://push.example.com/1", p256dh="k", auth="a"
    )
    return svet


def dnes(hodina, minuta=0):
    return datetime.combine(timezone.now().date(), time(hodina, minuta), tzinfo=UTC)


def let_ve_vzduchu(svet, vzlet, letadlo=None):
    let = Let.objects.create(
        letadlo=letadlo or svet.motor,
        ucel=Ucel.NORMALNI,
        misto_vzletu=svet.lkkl,
        platce=svet.pilot,
        zalozil=svet.casomeric,
        stav=StavLetu.VE_VZDUCHU,
        cas_vzletu=vzlet,
    )
    let.posadka.create(osoba=svet.pilot, funkce="pic")
    return let


def test_let_pres_maximalni_dobu(lide, odeslane):
    let = let_ve_vzduchu(lide, dnes(6))  # OK-TCS má max. dobu 5 hodin
    assert kontrola(dnes(10, 59)) == []
    [u] = kontrola(dnes(11, 1))
    assert u.druh == Upozorneni.Druh.MAX_DOBA
    assert u.prijemci == {"e-maily": 2, "push": 1}  # pilot i časoměřič, který let založil
    assert sorted(m.to[0] for m in mail.outbox) == ["cas@example.com", "pilot@example.com"]
    assert "déle než max. doba" in mail.outbox[0].subject
    assert odeslane[0][1]["titulek"] == "OK-TCS: déle než max. doba letu"
    assert '5°1"' in odeslane[0][1]["text"]

    # Každý druh jen jednou; v historii letu je záznam.
    assert kontrola(dnes(11, 6)) == []
    assert AuditLog.objects.get(akce="upozorneni", objekt_id=let.pk).duvod.startswith("Déle")


def test_let_po_soumraku(lide, odeslane):
    soumrak = slunce(timezone.now().date())["soumrak"]
    let_ve_vzduchu(lide, soumrak - timedelta(minutes=30), letadlo=lide.dvoumistne)
    assert kontrola(soumrak - timedelta(minutes=1)) == []
    [u] = kontrola(soumrak + timedelta(minutes=1))
    assert u.druh == Upozorneni.Druh.SOUMRAK
    assert "po soumraku" in odeslane[0][1]["titulek"]


def test_neukonceny_let_z_minuleho_dne(lide, odeslane):
    vcera = dnes(10) - timedelta(days=1)
    let_ve_vzduchu(lide, vcera, letadlo=lide.dvoumistne)
    pripraveny = Let.objects.create(
        letadlo=lide.kluzak,
        ucel=Ucel.NORMALNI,
        zpusob_vzletu="navijak",
        misto_vzletu=lide.lkkl,
        platce=lide.pilot,
        zalozil=lide.pilot,
        stav=StavLetu.PRIPRAVEN,
    )
    Let.objects.filter(pk=pripraveny.pk).update(zalozeno=vcera)
    druhy = sorted(u.druh for u in kontrola(dnes(7)))
    # Let ve vzduchu od včerejška je i po soumraku; připravený jen neukončený.
    assert druhy == ["neukonceny", "neukonceny", "soumrak"]
    assert any("zůstal připravený" in z[1]["text"] for z in odeslane)


def test_e_maily_jen_podle_rezimu(lide, odeslane):
    nastaveni = Nastaveni.aktualni()
    nastaveni.email_rezim = EmailRezim.VYPNUTO
    nastaveni.save()
    let_ve_vzduchu(lide, dnes(6))
    [u] = kontrola(dnes(11, 1))
    assert mail.outbox == [] and u.prijemci == {"e-maily": 0, "push": 1}


def test_zrusene_zarizeni_se_smaze(lide, monkeypatch):
    class Odpoved:
        status_code = 410

    def webpush(**kw):
        raise WebPushException("pryč", response=Odpoved())

    monkeypatch.setattr(push, "webpush", webpush)
    assert push.poslat(lide.pilot, "x", "y") == 0
    assert not PushOdber.objects.exists()


def test_zapnuti_upozorneni_na_zarizeni(jako, svet, odeslane):
    klient = jako(svet.pilot)
    stav = klient.get("/api/ucet/push").json()
    assert stav["zarizeni"] == 0 and len(stav["klic"]) == 87  # 65 bajtů v base64url

    odber = {"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "p", "auth": "a"}}
    assert post(klient, "/api/ucet/push", odber).json()["zarizeni"] == 1
    assert post(klient, "/api/ucet/push/zkouska").json() == {"pocet": 1}
    assert odeslane[0][1]["titulek"] == "LKKL Log – zkouška"

    # Stejné zařízení po přihlášení jiného uživatele patří jemu.
    post(jako(svet.casomeric), "/api/ucet/push", odber)
    assert PushOdber.objects.get().osoba == svet.casomeric

    assert post(klient, "/api/ucet/push", {**odber, "endpoint": "http://x"}).status_code == 400
    klient = jako(svet.casomeric)
    post(klient, "/api/ucet/push/vypnout", {"endpoint": odber["endpoint"]})
    assert not PushOdber.objects.exists()


def test_vapid_klic_z_secret_key(settings):
    puvodni = push.verejny_klic()
    push._soukromy_klic.cache_clear()
    settings.SECRET_KEY = "jiny-tajny-klic"
    try:
        assert push.verejny_klic() != puvodni
    finally:
        push._soukromy_klic.cache_clear()


def test_externi_osoba_upozorneni_nedostane(lide, odeslane):
    externi = Osoba.objects.create_user(None, jmeno="X", prijmeni="Y", externi=True)
    let = let_ve_vzduchu(lide, dnes(6))
    let.posadka.create(osoba=externi, funkce="prezkouseny")
    from lety.upozorneni import prijemci

    assert externi not in prijemci(let)
