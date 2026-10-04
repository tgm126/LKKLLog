from datetime import timedelta

import pytest
from django.utils import timezone

from lety.models import Let, StavLetu, Ucel

from .pomocne import post, ve_vzduchu

pytestmark = pytest.mark.django_db


def test_touch_and_go_behem_letu(jako, svet):
    let = ve_vzduchu(svet)
    klient = jako(svet.casomeric)
    odpoved = post(klient, f"/api/lety/{let.pk}/tg")
    assert odpoved.status_code == 200, odpoved.json()
    data = odpoved.json()
    assert data["pocet_tg"] == 1 and len(data["casy_tg"]) == 1
    assert data["pocet_pristani"] == 0  # ještě nepřistál

    # Dvojí ťuknutí se nezapíše dvakrát.
    odpoved = post(klient, f"/api/lety/{let.pk}/tg")
    assert odpoved.status_code == 409 and odpoved.json()["kod"] == "uz_zapsano"

    Let.objects.filter(pk=let.pk).update(casy_tg=[timezone.now() - timedelta(minutes=5)])
    assert post(klient, f"/api/lety/{let.pk}/tg").json()["pocet_tg"] == 2

    data = post(klient, f"/api/lety/{let.pk}/pristani", {"pocet_tg": 2}).json()
    assert data["pocet_pristani"] == 3 and len(data["casy_tg"]) == 2


def test_snizeni_poctu_tg_zahodi_casy(jako, svet):
    let = ve_vzduchu(svet)
    klient = jako(svet.casomeric)
    post(klient, f"/api/lety/{let.pk}/tg")
    data = post(klient, f"/api/lety/{let.pk}/pristani", {"pocet_tg": 0}).json()
    assert data["pocet_tg"] == 0 and data["casy_tg"] == [] and data["pocet_pristani"] == 1


def test_zpet_vrati_touch_and_go(jako, svet):
    let = ve_vzduchu(svet)
    klient = jako(svet.casomeric)
    data = post(klient, f"/api/lety/{let.pk}/tg").json()
    data = post(klient, f"/api/lety/{let.pk}/zpet", {"verze": data["verze"]}).json()
    assert data["pocet_tg"] == 0 and data["casy_tg"] == []
    assert data["stav"] == StavLetu.VE_VZDUCHU


def test_kluzak_touch_and_go_nedela(jako, svet):
    let = Let.objects.create(
        letadlo=svet.kluzak,
        ucel=Ucel.NORMALNI,
        zpusob_vzletu="navijak",
        misto_vzletu=svet.lkkl,
        platce=svet.pilot,
        zalozil=svet.pilot,
        stav=StavLetu.VE_VZDUCHU,
        cas_vzletu=timezone.now() - timedelta(minutes=10),
    )
    let.posadka.create(osoba=svet.pilot, funkce="pic")
    klient = jako(svet.casomeric)
    assert post(klient, f"/api/lety/{let.pk}/tg").status_code == 400
    odpoved = post(klient, f"/api/lety/{let.pk}/pristani", {"pocet_tg": 1})
    assert odpoved.status_code == 400
    assert "Kluzák" in odpoved.json()["detail"]


def test_tg_jen_ve_vzduchu_a_jen_posadka_nebo_casomeric(jako, svet):
    let = ve_vzduchu(svet)
    assert post(jako(svet.cizi_pilot), f"/api/lety/{let.pk}/tg").status_code == 403
    Let.objects.filter(pk=let.pk).update(
        stav=StavLetu.UKONCEN, cas_pristani=timezone.now(), misto_pristani=svet.lkkl
    )
    assert post(jako(svet.casomeric), f"/api/lety/{let.pk}/tg").status_code == 409
