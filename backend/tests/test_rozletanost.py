from datetime import UTC, datetime, time, timedelta

import pytest
from django.utils import timezone

from lety.rozletanost import CHYBA, OK, POZOR, kontroly, plus_mesice
from osoby.models import DruhKvalifikace, Licence, Medical, TridaMedicalu, TypLicence
from provoz.models import Nastaveni

from .pomocne import let_v, post

pytestmark = pytest.mark.django_db

DNES = timezone.now().date()


def pred(dny: int) -> datetime:
    return datetime.combine(DNES - timedelta(days=dny), time(10), tzinfo=UTC)


def licence(osoba, typ, *kvalifikace):
    lic = Licence.objects.create(osoba=osoba, typ=typ)
    for druh, platnost in kvalifikace:
        lic.kvalifikace.create(druh=druh, platnost_do=platnost)
    return lic


def medical(osoba, dni=365):
    Medical.objects.create(
        osoba=osoba, trida=TridaMedicalu.T2, platnost_do=DNES + timedelta(days=dni)
    )


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
    Licence.objects.all().delete()
    licence(svet.cizi_pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    k = podle_nazvu(svet.cizi_pilot)["Cestující – motorové"]
    assert k.stav == POZOR


def test_ppl_platnost_kvalifikace_a_prodlouzeni(svet):
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES - timedelta(days=1)))
    assert podle_nazvu(svet.pilot)["Kvalifikace SEP (land)"].stav == CHYBA

    Licence.objects.all().delete()
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
    assert "Test Pilot: nemá platnou jazykovou způsobilost." in varovani
    licence(svet.pilot, TypLicence.JAZYK, (DruhKvalifikace.CS_6, None))
    varovani = post(klient, "/api/kontrola-posadky", let).json()["varovani"]
    assert len(varovani) == 1 and "nesmí vozit cestující" in varovani[0]
    # Bez cestujících je všechno v pořádku.
    bez_hostu = post(klient, "/api/kontrola-posadky", {**let, "pocet_hostu": 0}).json()
    assert bez_hostu == {"varovani": []}


def test_sprava_vlastnich_licenci(jako, svet):
    klient = jako(svet.pilot)
    stav = klient.get("/api/ucet/licence").json()
    assert stav["licence"] == [] and [v["hodnota"] for v in stav["kvalifikace"]["ppl_a"]] == [
        "sep",
        "tmg",
    ]
    data = {
        "typ": "ppl_a",
        "cislo": "CZ.FCL.123",
        "kvalifikace": [{"druh": "sep", "platnost_do": "2027-05-31"}],
    }
    stav = post(klient, "/api/ucet/licence", data).json()
    [lic] = stav["licence"]
    assert lic["kvalifikace"] == [{"druh": "sep", "platnost_do": "2027-05-31"}]

    assert post(klient, "/api/ucet/licence", data).status_code == 400  # podruhé stejný typ
    spatne = {**data, "typ": "spl", "kvalifikace": [{"druh": "sep"}]}
    assert post(klient, "/api/ucet/licence", spatne).status_code == 400

    zmena = {**data, "id": lic["id"], "kvalifikace": [{"druh": "tmg", "platnost_do": None}]}
    stav = post(klient, "/api/ucet/licence", zmena).json()
    assert stav["licence"][0]["kvalifikace"] == [{"druh": "tmg", "platnost_do": None}]

    # Cizí licenci pilot nezmění ani nesmaže.
    cizi = jako(svet.cizi_pilot)
    assert post(cizi, "/api/ucet/licence", zmena).status_code == 404
    post(cizi, f"/api/ucet/licence/{lic['id']}/smazat")
    assert Licence.objects.count() == 1

    stav = post(klient, "/api/ucet/medical", {"trida": "2", "platnost_do": "2028-01-31"}).json()
    [med] = stav["medicaly"]
    stav = post(
        klient, "/api/ucet/medical", {"id": med["id"], "trida": "2", "platnost_do": "2029-01-31"}
    ).json()
    assert stav["medicaly"][0]["platnost_do"] == "2029-01-31"
    assert post(klient, f"/api/ucet/medical/{med['id']}/smazat").json()["medicaly"] == []


def test_medical_podle_tridy_pro_licenci(svet):
    """PPL(A) potřebuje třídu 2, SPL stačí LAPL – jedno osvědčení, dvě platnosti."""
    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    licence(svet.pilot, TypLicence.SPL, (DruhKvalifikace.NAVIJAK, None))
    Medical.objects.create(
        osoba=svet.pilot, trida=TridaMedicalu.T2, platnost_do=DNES - timedelta(days=5)
    )
    Medical.objects.create(
        osoba=svet.pilot, trida=TridaMedicalu.LAPL, platnost_do=DNES + timedelta(days=200)
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


def test_jazykova_zpusobilost(jako, svet):
    licence(
        svet.pilot,
        TypLicence.JAZYK,
        (DruhKvalifikace.EN_4, DNES + timedelta(days=60)),
        (DruhKvalifikace.CS_6, None),
    )
    k = podle_nazvu(svet.pilot)
    assert k["Angličtina – úroveň 4"].stav == POZOR  # 3 měsíce předem
    assert k["Čeština – úroveň 6"].text == "Platí trvale."

    # Prošlá angličtina nevadí, když platí čeština.
    Licence.objects.all().delete()
    licence(
        svet.pilot,
        TypLicence.JAZYK,
        (DruhKvalifikace.EN_4, DNES - timedelta(days=1)),
        (DruhKvalifikace.CS_6, None),
    )
    from lety.rozletanost import varovani_pilota
    from osoby.models import Kategorie

    licence(svet.pilot, TypLicence.PPL_A, (DruhKvalifikace.SEP, DNES + timedelta(days=300)))
    assert not any("jazyk" in v for v in varovani_pilota(svet.pilot, Kategorie.MOTOR, False))

    # Dvě úrovně téhož jazyka nejdou.
    data = {"typ": "jazyk", "kvalifikace": [{"druh": "en_4"}, {"druh": "en_5"}]}
    Licence.objects.all().delete()
    assert post(jako(svet.pilot), "/api/ucet/licence", data).status_code == 400


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
