from datetime import UTC, datetime, time, timedelta

import pytest
from django.utils import timezone

from lety.rozletanost import CHYBA, OK, POZOR, kontroly, plus_mesice
from osoby.models import DruhKvalifikace, PrukazOsoby, TridaMedicalu, TypLicence
from provoz.models import Nastaveni

from .pomocne import let_v, post, prukaz

pytestmark = pytest.mark.django_db

DNES = timezone.now().date()


def pred(dny: int) -> datetime:
    return datetime.combine(DNES - timedelta(days=dny), time(10), tzinfo=UTC)


def licence(osoba, typ, *kvalifikace):
    return prukaz(osoba, typ, *kvalifikace)


def medical(osoba, dni=365):
    prukaz(osoba, "medical", (TridaMedicalu.T2, DNES + timedelta(days=dni)))


def podle_nazvu(osoba):
    return {k.nazev: k for k in kontroly(osoba, DNES)}


def test_bez_licence_a_medicalu(svet):
    k = podle_nazvu(svet.pilot)
    assert k["Medical"].stav == CHYBA and k["Licence"].stav == CHYBA


def test_medical_brzy_vyprsi(svet):
    medical(svet.pilot, dni=10)
    assert podle_nazvu(svet.pilot)["Medical"].stav == POZOR


def test_lapl_prubezna_rozletanost(svet):
    licence(svet.pilot, TypLicence.LAPL_A, (DruhKvalifikace.SEP, None))
    for i in range(12):  # 12 letů po hodině jako PIC
        let_v(svet, pred(30 + i * 10), minut=60)
    k = podle_nazvu(svet.pilot)["Průběžná rozlétanost"]
    assert k.stav == CHYBA  # chybí hodina s instruktorem
    assert any("✗ s instruktorem" in p for p in k.podrobnosti)

    vycvik = let_v(svet, pred(400), minut=60, pilot=svet.instruktor)
    vycvik.posadka.create(osoba=svet.pilot, funkce="zak")
    k = podle_nazvu(svet.pilot)["Průběžná rozlétanost"]
    assert k.stav == OK
    # Platí do: nejdřív vypadne let s instruktorem (před 400 dny) – za 24 měsíců od něj.
    assert k.plati_do == plus_mesice(DNES - timedelta(days=400), 24)


def test_cestujici_tri_vzlety_za_90_dni_i_s_tg(svet):
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    let_v(svet, pred(20), minut=40, pocet_tg=2)  # 1 let se 2× T&G = 3 vzlety a přistání
    k = podle_nazvu(svet.pilot)["Cestující – motorové"]
    assert k.stav == OK and k.plati_do == DNES - timedelta(days=20) + timedelta(days=90)

    let_v(svet, pred(100), minut=40, pocet_tg=5)  # mimo 90 dní se nepočítá
    PrukazOsoby.objects.all().delete()
    licence(svet.cizi_pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    k = podle_nazvu(svet.cizi_pilot)["Cestující – motorové"]
    assert k.stav == POZOR


def test_ppl_platnost_kvalifikace_a_prodlouzeni(svet):
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES - timedelta(days=1)))
    assert podle_nazvu(svet.pilot)["Kvalifikace SEP (land)"].stav == CHYBA

    PrukazOsoby.objects.all().delete()
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=100)))
    let_v(svet, pred(10), minut=90)
    k = podle_nazvu(svet.pilot)["Kvalifikace SEP (land)"]
    assert k.stav == OK
    assert k.podrobnosti[0] == "Pro prodloužení zkušeností:"
    assert '✗ doba celkem 1°30" / 12°0"' in k.podrobnosti


def test_spl_kluzaky_a_zpusoby_vzletu(svet):
    licence(
        svet.pilot,
        TypLicence.SPL,
        (DruhKvalifikace.NAVIJAK, None),
        (DruhKvalifikace.VLEK, None),
    )
    for i in range(15):
        let_v(svet, pred(5 + i), minut=20, letadlo=svet.kluzak, zpusob_vzletu="navijak")
    for i in range(2):
        vycvik = let_v(
            svet,
            pred(50 + i),
            minut=10,
            letadlo=svet.kluzak,
            pilot=svet.instruktor,
            zpusob_vzletu="navijak",
        )
        vycvik.posadka.create(osoba=svet.pilot, funkce="zak")
    k = podle_nazvu(svet.pilot)
    assert k["Rozlétanost na kluzácích"].stav == OK
    assert k["Způsob vzletu: naviják / auto"].stav == OK
    assert k["Způsob vzletu: aerovlek"].stav == CHYBA
    assert k["Cestující – kluzák"].stav == OK


def test_ull_platnost(svet):
    licence(svet.pilot, TypLicence.ULL, (DruhKvalifikace.ULL, DNES - timedelta(days=100)))
    k = podle_nazvu(svet.pilot)["Platnost průkazu"]
    assert k.stav == CHYBA
    assert any("inspektorem" in p for p in k.podrobnosti)


def test_rozletanost_vidi_jen_admin_dokud_je_hlidani_vypnute(jako, svet):
    data = jako(svet.pilot).get("/api/nalet/rozletanost").json()
    vypnuto = {"zpusobilost": False, "rozletanost": False}
    assert data == {"moduly": vypnuto, "zobrazit": False, "kontroly": []}
    svet.pilot.is_staff = True
    svet.pilot.save()
    assert jako(svet.pilot).get("/api/nalet/rozletanost").json()["zobrazit"] is True

    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_zpusobilost = nastaveni.hlidat_rozletanost = True
    nastaveni.save()
    data = jako(svet.cizi_pilot).get("/api/nalet/rozletanost").json()
    assert data["zobrazit"] is True
    assert data["kontroly"][0]["nazev"] == "Medical"


def test_varovani_pri_zakladani_letu(jako, svet):
    klient = jako(svet.casomeric)
    let = {
        "letadlo_id": svet.motor.pk,
        "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}],
        "pocet_hostu": 1,
    }
    assert post(klient, "/api/kontrola-posadky", let).json() == {"varovani": []}  # vypnuto

    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_zpusobilost = nastaveni.hlidat_rozletanost = True
    nastaveni.save()
    varovani = post(klient, "/api/kontrola-posadky", let).json()["varovani"]
    assert varovani == ["Test Pilot: nemá zadanou licenci pro kategorii motorové."]

    medical(svet.pilot)
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    varovani = post(klient, "/api/kontrola-posadky", let).json()["varovani"]
    assert "Test Pilot: nemá zadaný radiofonní průkaz." in varovani
    licence(svet.pilot, TypLicence.RADIO, (DruhKvalifikace.OFL, DNES + timedelta(days=3000)))
    varovani = post(klient, "/api/kontrola-posadky", let).json()["varovani"]
    assert len(varovani) == 1 and "nesmí vozit cestující" in varovani[0]
    # Bez cestujících je všechno v pořádku.
    bez_hostu = post(klient, "/api/kontrola-posadky", {**let, "pocet_hostu": 0}).json()
    assert bez_hostu == {"varovani": []}


def test_medical_podle_tridy_pro_licenci(svet):
    """PPL(A) potřebuje třídu 2, SPL stačí LAPL – jedno osvědčení, dvě platnosti."""
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    licence(svet.pilot, TypLicence.SPL, (DruhKvalifikace.NAVIJAK, None))
    prukaz(
        svet.pilot,
        "medical",
        (TridaMedicalu.T2, DNES - timedelta(days=5)),
        (TridaMedicalu.LAPL, DNES + timedelta(days=200)),
    )
    k = podle_nazvu(svet.pilot)
    assert k["Medical pro PPL(A)"].stav == CHYBA
    assert k["Medical pro SPL"].stav == OK

    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_zpusobilost = nastaveni.hlidat_rozletanost = True
    nastaveni.save()
    from lety.rozletanost import varovani_pilota
    from osoby.models import Kategorie

    motor = varovani_pilota(svet.pilot, Kategorie.MOTOR, False)
    kluzak = varovani_pilota(svet.pilot, Kategorie.KLUZAK, False, "navijak")
    assert any("Medical pro PPL(A)" in v for v in motor)
    assert not any("Medical" in v for v in kluzak)


def test_radiofonni_prukaz(svet):
    assert podle_nazvu(svet.pilot)["Radiofonní průkaz"].text == "Není zadaný."
    licence(svet.pilot, TypLicence.RADIO, (DruhKvalifikace.OFL, DNES + timedelta(days=45)))
    k = podle_nazvu(svet.pilot)["Omezený (OFL)"]
    assert k.stav == POZOR  # žádost se podává měsíc předem – varuje se 2 měsíce dopředu
    assert "ČTÚ" in k.podrobnosti[0]


def test_anglictina_icao_jen_informace(jako, svet):
    """Provoz aeroklubu je česky – angličtina se jen eviduje, nehlídá ani nevaruje."""
    from lety.rozletanost import INFO, varovani_pilota
    from osoby.models import Kategorie

    medical(svet.pilot)
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    licence(svet.pilot, TypLicence.RADIO, (DruhKvalifikace.OFL, DNES + timedelta(days=3000)))
    assert "Angličtina" not in {k.oblast for k in kontroly(svet.pilot, DNES)}
    licence(svet.pilot, TypLicence.JAZYK, (DruhKvalifikace.EN_4, DNES - timedelta(days=1)))
    k = podle_nazvu(svet.pilot)["Angličtina ICAO 4"]
    assert k.stav == INFO and k.text.startswith("Neplatí od")
    assert varovani_pilota(svet.pilot, Kategorie.MOTOR, False) == []


def test_moduly_zpusobilost_a_rozletanost_zvlast(jako, svet):
    medical(svet.pilot)
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES - timedelta(days=1)))
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_rozletanost = True
    nastaveni.save()
    data = jako(svet.pilot).get("/api/nalet/rozletanost").json()
    assert {k["modul"] for k in data["kontroly"]} == {"rozletanost"}

    let = {
        "letadlo_id": svet.motor.pk,
        "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}],
        "pocet_hostu": 1,
    }
    varovani = post(jako(svet.casomeric), "/api/kontrola-posadky", let).json()["varovani"]
    # Jen rozlétanost (cestující); prošlá kvalifikace SEP patří ke způsobilosti.
    assert len(varovani) == 1 and "cestující" in varovani[0]


def test_varovani_na_prosly_termin_letadla(jako, svet):
    from lety.models import TerminLetadla

    TerminLetadla.objects.create(letadlo=svet.motor, nazev="ARC", datum=DNES - timedelta(days=2))
    let = {"letadlo_id": svet.motor.pk, "posadka": [{"osoba_id": svet.pilot.pk, "funkce": "pic"}]}
    klient = jako(svet.casomeric)
    assert post(klient, "/api/kontrola-posadky", let).json() == {"varovani": []}
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_letadla = True
    nastaveni.save()
    [varovani] = post(klient, "/api/kontrola-posadky", let).json()["varovani"]
    assert varovani.startswith("OK-TCS: ARC – prošlo")


def test_zak_pred_solem_potrebuje_medical_a_radiofonni_prukaz(jako, svet):
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_zpusobilost = True
    nastaveni.save()
    solo = {
        "letadlo_id": svet.motor.pk,
        "ucel": "vycvik_solo",
        "posadka": [
            {"osoba_id": svet.zak.pk, "funkce": "pic"},
            {"osoba_id": svet.instruktor.pk, "funkce": "dozor"},
        ],
    }
    klient = jako(svet.casomeric)
    varovani = post(klient, "/api/kontrola-posadky", solo).json()["varovani"]
    assert varovani == [
        "Test Žák: před sólem musí mít platný medical.",
        "Test Žák: před sólem musí mít platný radiofonní průkaz.",
    ]  # o licenci ani rozlétanosti u žáka ne
    medical(svet.zak)
    licence(svet.zak, TypLicence.RADIO, (DruhKvalifikace.OFL, DNES + timedelta(days=3000)))
    assert post(klient, "/api/kontrola-posadky", solo).json() == {"varovani": []}


def test_vlekani_pet_vleku_za_24_mesicu(svet):
    from lety.models import Letadlo, Ucel
    from lety.rozletanost import varovani_pilota
    from osoby.models import Kategorie

    licence(
        svet.pilot,
        TypLicence.PPL_A,
        (DruhKvalifikace.SEP, DNES + timedelta(days=300)),
        (DruhKvalifikace.VLEKANI, None),
    )
    k = podle_nazvu(svet.pilot)
    assert "Kvalifikace Vlekání kluzáků" not in k  # vlekání nemá datum platnosti
    assert k["Vlekání kluzáků"].stav == CHYBA

    # Na obyčejném letu se rozlétanost vlekaře nehlásí, při vleku ano.
    obycejny = varovani_pilota(svet.pilot, Kategorie.MOTOR, False)
    vlek = varovani_pilota(svet.pilot, Kategorie.MOTOR, False, vlek=True)
    assert not any("Vlekání" in v for v in obycejny)
    assert any("Vlekání" in v for v in vlek)

    vlecna = Letadlo.objects.create(
        imatrikulace="OK-VLK", typ="Zlin", kategorie=Kategorie.MOTOR, vlecne=True
    )
    for i in range(5):
        let_v(svet, pred(10 + i), minut=8, letadlo=vlecna, ucel=Ucel.VLEK)
    assert podle_nazvu(svet.pilot)["Vlekání kluzáků"].stav == OK
