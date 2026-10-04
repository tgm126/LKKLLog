from datetime import timedelta

import pytest
from django.utils import timezone

from lety.models import Let, Letadlo, StavLetu, Ucel
from osoby.models import Kategorie

from .pomocne import osoba, post, ve_vzduchu

pytestmark = pytest.mark.django_db


@pytest.fixture
def vlecna(svet):
    return Letadlo.objects.create(
        imatrikulace="OK-TZL", typ="Zlin", kategorie=Kategorie.MOTOR, pocet_mist=2, vlecne=True
    )


@pytest.fixture
def vlekar(svet):
    return osoba("Vlekař")


def kluzak_ve_vleku(svet, vlecna, vlekar, **kw):
    data = {
        "letadlo_id": svet.kluzak.pk,
        "ucel": Ucel.NORMALNI,
        "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}],
        "zpusob_vzletu": "vlek",
        "vlek": {"letadlo_id": vlecna.pk, "vlekar_id": vlekar.pk},
    }
    data.update(kw)
    return data


def test_vlek_zalozi_dvojici_se_spolecnym_vzletem(jako, svet, vlecna, vlekar):
    odpoved = post(jako(svet.casomeric), "/api/lety", kluzak_ve_vleku(svet, vlecna, vlekar))
    assert odpoved.status_code == 200, odpoved.json()
    kluzak = odpoved.json()
    assert kluzak["stav"] == StavLetu.VE_VZDUCHU
    assert kluzak["vlek"] == "vlek OK-TZL (Test Vlekař)"

    tah = Let.objects.get(pk=kluzak["vlek_id"])
    assert tah.ucel == Ucel.VLEK
    assert tah.cas_vzletu == Let.objects.get(pk=kluzak["id"]).cas_vzletu
    assert tah.platce_id == svet.pilot.pk  # vlek platí plátce kluzáku
    prehled = jako(svet.casomeric).get("/api/prehled").json()
    popis_tahu = next(x["vlek"] for x in prehled["lety"] if x["id"] == tah.pk)
    assert popis_tahu == "vleče OK-T101 (Test Pilot)"


def test_pripravena_dvojice_startuje_spolecne(jako, svet, vlecna, vlekar):
    klient = jako(svet.casomeric)
    kluzak = post(klient, "/api/lety", kluzak_ve_vleku(svet, vlecna, vlekar, akce="pripravit"))
    kluzak = kluzak.json()
    assert Let.objects.get(pk=kluzak["vlek_id"]).stav == StavLetu.PRIPRAVEN

    assert post(klient, f"/api/lety/{kluzak['id']}/vzlet").status_code == 200
    assert Let.objects.get(pk=kluzak["vlek_id"]).stav == StavLetu.VE_VZDUCHU
    druhy = post(klient, f"/api/lety/{kluzak['vlek_id']}/vzlet")
    assert druhy.status_code == 409 and druhy.json()["kod"] == "uz_zapsano"


def test_pristavaji_kazdy_zvlast(jako, svet, vlecna, vlekar):
    klient = jako(svet.casomeric)
    kluzak = post(klient, "/api/lety", kluzak_ve_vleku(svet, vlecna, vlekar)).json()
    assert post(klient, f"/api/lety/{kluzak['vlek_id']}/pristani", {"kratky_let": "normalni"})
    assert Let.objects.get(pk=kluzak["vlek_id"]).stav == StavLetu.UKONCEN
    assert Let.objects.get(pk=kluzak["id"]).stav == StavLetu.VE_VZDUCHU


def test_zpet_po_zalozeni_zrusi_oba(jako, svet, vlecna, vlekar):
    klient = jako(svet.casomeric)
    kluzak = post(klient, "/api/lety", kluzak_ve_vleku(svet, vlecna, vlekar)).json()
    post(klient, f"/api/lety/{kluzak['id']}/zpet", {"verze": kluzak["verze"]})
    assert set(Let.objects.values_list("stav", flat=True)) == {StavLetu.ZRUSEN}


@pytest.mark.parametrize(
    ("uprava", "chyba"),
    [
        ({"vlek": None}, "vyberte vlečné letadlo"),
        ({"vlek": {"letadlo_id": 0, "vlekar_id": 0}}, "vyberte vlečné letadlo"),
    ],
)
def test_vlek_bez_udaju(jako, svet, vlecna, vlekar, uprava, chyba):
    data = kluzak_ve_vleku(svet, vlecna, vlekar, **uprava)
    odpoved = post(jako(svet.casomeric), "/api/lety", data)
    assert odpoved.status_code == 400
    assert chyba in odpoved.json()["detail"]


def test_vlek_pravidla(jako, svet, vlecna, vlekar):
    klient = jako(svet.casomeric)
    # Letadlo, které nemůže vlekat.
    data = kluzak_ve_vleku(svet, vlecna, vlekar)
    data["vlek"] = {"letadlo_id": svet.motor.pk, "vlekar_id": vlekar.pk}
    assert post(klient, "/api/lety", data).status_code == 400
    # Vlekař nemůže být v posádce kluzáku.
    data = kluzak_ve_vleku(svet, vlecna, svet.pilot)
    assert "Vlekař nemůže" in post(klient, "/api/lety", data).json()["detail"]
    # Vlek u motorového letadla nedává smysl.
    data = kluzak_ve_vleku(svet, vlecna, vlekar, letadlo_id=svet.motor.pk)
    assert post(klient, "/api/lety", data).status_code == 400
    # Přímé založení letu s účelem vlek.
    data = {
        "letadlo_id": vlecna.pk,
        "ucel": "vlek",
        "posadka": [{"osoba_id": vlekar.pk, "funkce": "pic"}],
    }
    assert post(klient, "/api/lety", data).status_code == 400


def test_vlekar_ve_vzduchu_nemuze_vlekat(jako, svet, vlecna):
    ve_vzduchu(svet)  # Test Pilot letí na OK-TCS
    data = kluzak_ve_vleku(svet, vlecna, svet.pilot)
    data["posadka"] = [{"osoba_id": svet.instruktor.pk, "funkce": "pic"}]
    odpoved = post(jako(svet.casomeric), "/api/lety", data)
    assert odpoved.status_code == 409 and odpoved.json()["kod"] == "osoba_obsazena"


def test_dopsany_vlek_potrebuje_pristani_vlecne(jako, svet, vlecna, vlekar):
    ted = timezone.now().replace(microsecond=0)
    data = kluzak_ve_vleku(
        svet,
        vlecna,
        vlekar,
        akce="dopsat",
        cas_vzletu=(ted - timedelta(hours=2)).isoformat(),
        cas_pristani=(ted - timedelta(hours=1)).isoformat(),
    )
    klient = jako(svet.casomeric)
    assert post(klient, "/api/lety", data).status_code == 400
    data["vlek"]["cas_pristani"] = (ted - timedelta(hours=1, minutes=50)).isoformat()
    kluzak = post(klient, "/api/lety", data).json()
    tah = Let.objects.get(pk=kluzak["vlek_id"])
    assert tah.stav == StavLetu.UKONCEN and tah.doba_min == 10
    assert kluzak["doba_min"] == 60


def test_oprava_neprepne_vlek(jako, svet, vlecna, vlekar):
    klient = jako(svet.casomeric)
    kluzak = post(klient, "/api/lety", kluzak_ve_vleku(svet, vlecna, vlekar)).json()
    oprava = {
        "letadlo_id": kluzak["letadlo_id"],
        "ucel": kluzak["ucel"],
        "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}],
        "zpusob_vzletu": "navijak",
        "misto_vzletu_id": kluzak["misto_vzletu_id"],
        "cas_vzletu": kluzak["cas_vzletu"],
        "verze": kluzak["verze"],
        "duvod": "jine",
    }
    odpoved = post(klient, f"/api/lety/{kluzak['id']}/oprava", oprava)
    assert odpoved.status_code == 400 and "vleku" in odpoved.json()["detail"]

    tah = Let.objects.get(pk=kluzak["vlek_id"])
    oprava_tahu = {
        "letadlo_id": svet.motor.pk,
        "ucel": "vlek",
        "posadka": [{"osoba_id": vlekar.pk, "funkce": "pic"}],
        "misto_vzletu_id": tah.misto_vzletu_id,
        "cas_vzletu": kluzak["cas_vzletu"],
        "verze": tah.verze,
        "duvod": "chybne_letadlo",
    }
    odpoved = post(klient, f"/api/lety/{tah.pk}/oprava", oprava_tahu)
    assert odpoved.status_code == 400 and "vlekat" in odpoved.json()["detail"]
