import io
from datetime import UTC, datetime, timedelta

import pytest
from django.utils import timezone
from openpyxl import load_workbook

from lety.models import Let, Letadlo, StavLetu, Ucel
from osoby.models import Kategorie

from .pomocne import osoba

pytestmark = pytest.mark.django_db


def let(svet, vzlet, minut=30, letadlo=None, pilot=None, **kw):
    pilot = pilot or svet.pilot
    kw.setdefault("stav", StavLetu.UKONCEN)
    kw.setdefault("platce", pilot)
    novy = Let.objects.create(
        letadlo=letadlo or svet.motor,
        ucel=kw.pop("ucel", Ucel.NORMALNI),
        misto_vzletu=svet.lkkl,
        misto_pristani=svet.lkkl,
        cas_vzletu=vzlet,
        cas_pristani=vzlet + timedelta(minutes=minut),
        zalozil=pilot,
        **kw,
    )
    novy.posadka.create(osoba=pilot, funkce="pic")
    return novy


@pytest.fixture
def data(svet):
    """Říjen 2026: několik letů, jeden soukromý, jeden zrušený, vlek, aeroklub."""
    d = type("Data", (), {})()
    d.den = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)
    soukrome = Letadlo.objects.create(
        imatrikulace="OK-SOU", typ="Soukromý", kategorie=Kategorie.MOTOR, soukrome=True
    )
    d.vlecna = Letadlo.objects.create(
        imatrikulace="OK-TZL", typ="Zlin", kategorie=Kategorie.MOTOR, vlecne=True
    )
    d.vlekar = osoba("Vlekař")
    let(svet, d.den, minut=60, pocet_tg=3)
    let(svet, d.den + timedelta(hours=2), minut=20, plati_aeroklub=True, platce=None)
    let(svet, d.den + timedelta(hours=4), minut=45, letadlo=soukrome, soukrome=True)
    let(svet, d.den + timedelta(hours=5), minut=10, stav=StavLetu.ZRUSEN, duvod_zruseni="omyl")
    tah = let(
        svet,
        d.den + timedelta(hours=6),
        minut=8,
        letadlo=d.vlecna,
        pilot=d.vlekar,
        ucel=Ucel.VLEK,
        platce=svet.pilot,
    )
    let(
        svet,
        d.den + timedelta(hours=6),
        minut=40,
        letadlo=svet.kluzak,
        zpusob_vzletu="vlek",
        vlecny_let=tah,
    )
    let(
        svet,
        d.den + timedelta(hours=8),
        minut=0,
        letadlo=svet.kluzak,
        zpusob_vzletu="navijak",
        kratky_let="start_bez_doby",
    )
    let(svet, d.den - timedelta(days=10), minut=99)  # září – mimo období
    return d


ZARI_RIJEN = "od=2026-10-01&do=2026-10-31"


def test_vypis_obdobi_a_vychozi_filtry(jako, svet, data):
    vysledek = jako(svet.pilot).get(f"/api/vypis?{ZARI_RIJEN}").json()
    imatrikulace = [x["imatrikulace"] for x in vysledek["lety"]]
    assert "OK-SOU" not in imatrikulace  # soukromé ve výchozím stavu ne
    assert len(imatrikulace) == 5  # bez zrušeného a bez září
    assert vysledek["smi_exportovat"] is False

    vse = jako(svet.pilot).get(f"/api/vypis?{ZARI_RIJEN}&soukrome=true&zrusene=true").json()
    assert len(vse["lety"]) == 7


def test_souhrny(jako, svet, data):
    s = jako(svet.pilot).get(f"/api/vypis?{ZARI_RIJEN}").json()["souhrn"]
    assert s["celkem"] == {
        "lety": 5,
        "minuty": 60 + 20 + 8 + 40 + 0,
        "pristani": 4 + 1 + 1 + 1 + 1,  # první let: 3× T&G + přistání
        "tg": 3,
        "navijak": 1,
        "vlek": 1,
    }
    letadla = {(r["imatrikulace"], r["ucel"]): r["minuty"] for r in s["podle_letadel"]}
    assert letadla[("OK-TZL", "Vlek")] == 8
    assert letadla[("OK-T101", "Normální")] == 40  # start bez doby = 0 min
    platci = {r["platce"]: r["minuty"] for r in s["podle_platcu"]}
    assert platci == {"Aeroklub": 20, "Test Pilot": 60 + 8 + 40}


def test_filtry_osoby_platce_a_ucelu(jako, svet, data):
    klient = jako(svet.pilot)
    vlekar = klient.get(f"/api/vypis?{ZARI_RIJEN}&osoba={data.vlekar.pk}").json()
    assert [x["imatrikulace"] for x in vlekar["lety"]] == ["OK-TZL"]
    aeroklub = klient.get(f"/api/vypis?{ZARI_RIJEN}&platce=0").json()
    assert len(aeroklub["lety"]) == 1 and aeroklub["lety"][0]["plati_aeroklub"]
    vleky = klient.get(f"/api/vypis?{ZARI_RIJEN}&ucel=vlek").json()
    assert len(vleky["lety"]) == 1
    navijak = klient.get(f"/api/vypis?{ZARI_RIJEN}&zpusob=navijak").json()
    assert len(navijak["lety"]) == 1


def test_vychozi_obdobi_je_tento_mesic(jako, svet):
    vysledek = jako(svet.pilot).get("/api/vypis").json()
    dnes = timezone.now().date()
    assert vysledek["od"] == dnes.replace(day=1).isoformat()
    assert vysledek["do"] == dnes.isoformat()


def test_chybne_obdobi(jako, svet):
    klient = jako(svet.pilot)
    assert klient.get("/api/vypis?od=2026-10-31&do=2026-10-01").status_code == 400
    assert klient.get("/api/vypis?od=2024-01-01&do=2026-10-01").status_code == 400


def test_export_jen_ucetni_a_admin(jako, svet, data):
    assert jako(svet.pilot).get(f"/api/vypis/export.xlsx?{ZARI_RIJEN}").status_code == 403
    ucetni = osoba("Účetní", role_ucetni=True)
    odpoved = jako(ucetni).get(f"/api/vypis/export.xlsx?{ZARI_RIJEN}")
    assert odpoved.status_code == 200
    assert "lkkllog-vypis-2026-10-01-2026-10-31.xlsx" in odpoved["Content-Disposition"]

    wb = load_workbook(io.BytesIO(odpoved.content))
    assert wb.sheetnames == ["Lety", "Podle letadel", "Podle plátců", "Parametry"]
    lety = list(wb["Lety"].iter_rows(values_only=True))
    assert lety[0][0] == "Datum" and len(lety) == 1 + 5
    prvni = dict(zip(lety[0], lety[1], strict=True))
    assert prvni["Doba"] == '1°0"' and prvni["Přistání"] == 4 and prvni["Platí"] == "Test Pilot"
    parametry = dict(wb["Parametry"].iter_rows(min_row=2, values_only=True))
    assert parametry["Soukromá letadla"] == "bez"
    assert parametry["Vytvořil"] == "Test Účetní"
    celkem = list(wb["Podle plátců"].iter_rows(values_only=True))[-1]
    assert celkem[0] == "Celkem" and celkem[2] == 128


def test_export_csv(jako, svet, data):
    odpoved = jako(osoba("Účetní", role_ucetni=True)).get(f"/api/vypis/export.csv?{ZARI_RIJEN}")
    text = odpoved.content.decode("utf-8")
    assert text.startswith("﻿Datum;Letadlo;")
    assert text.count("\n") == 1 + 5
    assert "03.10.2026;OK-TCS" in text
