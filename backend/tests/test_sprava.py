from datetime import UTC, datetime, time, timedelta

import pytest
from django.utils import timezone

from lety.models import TerminLetadla
from osoby.models import Licence, Medical, Opravneni

from .pomocne import let_v, osoba, post

pytestmark = pytest.mark.django_db

DNES = timezone.now().date()


@pytest.fixture
def spravce(svet):
    return osoba("Správce", role_spravce=True)


def test_prehled_pilotu_jen_pro_spravce(jako, svet, spravce):
    Opravneni.objects.create(osoba=svet.pilot, kategorie="motor", uroven="pilot")
    assert jako(svet.pilot).get("/api/sprava/piloti").status_code == 403
    piloti = jako(spravce).get("/api/sprava/piloti").json()
    [pilot] = [p for p in piloti if p["id"] == svet.pilot.pk]
    assert pilot["stav"] == "chyba" and not pilot["testovaci"]
    assert "Medical: Není zadaný." in pilot["problemy"]
    detail = jako(spravce).get(f"/api/sprava/piloti/{svet.pilot.pk}").json()
    assert detail["kontroly"][0]["nazev"] == "Medical"


def test_spravce_upravi_licenci_a_medical_jinemu(jako, svet, spravce):
    url = f"/api/ucet/licence?osoba={svet.pilot.pk}"
    data = {"typ": "radio", "kvalifikace": [{"druh": "ofl", "platnost_do": "2034-01-31"}]}
    assert post(jako(svet.cizi_pilot), url, data).status_code == 403
    stav = post(jako(spravce), url, data).json()
    assert stav["jmeno"] == "Test Pilot" and stav["licence"][0]["typ"] == "radio"
    assert Licence.objects.get().osoba == svet.pilot

    tridy = {"tridy": {"2": "2027-03-31", "lapl": "2029-03-31", "1": None}}
    stav = post(jako(spravce), f"/api/ucet/medical/tridy?osoba={svet.pilot.pk}", tridy).json()
    assert {m["trida"]: m["platnost_do"] for m in stav["medicaly"]} == {
        "2": "2027-03-31",
        "lapl": "2029-03-31",
    }
    # Vymazání data třídu odebere.
    tridy = {"tridy": {"2": None, "lapl": "2029-03-31"}}
    post(jako(svet.pilot), "/api/ucet/medical/tridy", tridy)
    assert list(Medical.objects.values_list("trida", flat=True)) == ["lapl"]


def test_letadla_nalet_z_deniku_a_terminy(jako, svet, spravce):
    vcera = datetime.combine(DNES - timedelta(days=1), time(10), tzinfo=UTC)
    let_v(svet, vcera - timedelta(days=10), minut=50)  # před stavem deníku – nepočítá se
    let_v(svet, vcera, minut=40)
    klient = jako(spravce)
    denik = {
        "nalet_pocatek_min": 1199 * 60,
        "starty_pocatek": 3000,
        "stav_k": str(DNES - timedelta(days=5)),
    }
    letadla = post(klient, f"/api/sprava/letadla/{svet.motor.pk}/denik", denik).json()
    [motor] = [let for let in letadla if let["id"] == svet.motor.pk]
    assert motor["nalet_min"] == 1199 * 60 + 40 and motor["starty"] == 3001

    termin = {"letadlo_id": svet.motor.pk, "nazev": "100h prohlídka", "pri_naletu_h": 1200}
    letadla = post(klient, "/api/sprava/terminy", termin).json()
    [motor] = [let for let in letadla if let["id"] == svet.motor.pk]
    assert motor["terminy"][0]["stav"] == "pozor"
    assert motor["terminy"][0]["text"] == 'při 1200 h – zbývá 20"'

    arc = {"letadlo_id": svet.motor.pk, "nazev": "ARC", "datum": str(DNES - timedelta(days=1))}
    letadla = post(klient, "/api/sprava/terminy", arc).json()
    [motor] = [let for let in letadla if let["id"] == svet.motor.pk]
    assert {t["nazev"]: t["stav"] for t in motor["terminy"]}["ARC"] == "chyba"

    assert post(klient, "/api/sprava/terminy", {**arc, "datum": None}).status_code == 400
    assert jako(svet.pilot).get("/api/sprava/letadla").status_code == 403
    termin_id = TerminLetadla.objects.get(nazev="ARC").pk
    post(jako(spravce), f"/api/sprava/terminy/{termin_id}/smazat")
    assert TerminLetadla.objects.count() == 1


def test_zak_bez_licence_neni_chyba(jako, svet, spravce):
    Opravneni.objects.create(osoba=svet.zak, kategorie="motor", uroven="zak")
    piloti = jako(spravce).get("/api/sprava/piloti").json()
    [zak] = [p for p in piloti if p["id"] == svet.zak.pk]
    assert "Licence: Pilotní licence není zadaná." not in zak["problemy"]


def test_testovaci_licence(svet):
    from django.core.management import call_command

    from osoby.models import Kategorie, Uroven

    pilot = osoba("Testovací pilot", testovaci=True)
    Opravneni.objects.create(osoba=pilot, kategorie=Kategorie.MOTOR, uroven=Uroven.PILOT)
    Opravneni.objects.create(osoba=pilot, kategorie=Kategorie.KLUZAK, uroven=Uroven.PILOT)
    zak = osoba("Testovací žák", testovaci=True)
    Opravneni.objects.create(osoba=zak, kategorie=Kategorie.KLUZAK, uroven=Uroven.ZAK)
    Opravneni.objects.create(osoba=svet.pilot, kategorie=Kategorie.MOTOR, uroven=Uroven.PILOT)

    call_command("testovaci_licence")
    typy = set(Licence.objects.filter(osoba=pilot).values_list("typ", flat=True))
    assert "spl" in typy and typy & {"ppl_a", "lapl_a"}
    # Žák: bez pilotní licence, ale s medicalem a radiofonním průkazem (kvůli sólu).
    assert list(Licence.objects.filter(osoba=zak).values_list("typ", flat=True)) == ["radio"]
    assert zak.medicaly.exists()
    assert not Licence.objects.filter(osoba=svet.pilot).exists()  # skutečné osoby ne

    pocet = Licence.objects.count()
    call_command("testovaci_licence")  # bez --prepsat nic nového
    assert Licence.objects.count() == pocet


def test_testovaci_letadla(jako, svet, spravce):
    from django.core.management import call_command

    call_command("testovaci_letadla")
    letadla = {let["imatrikulace"]: let for let in jako(spravce).get("/api/sprava/letadla").json()}
    motor = letadla["OK-TCS"]
    assert not motor["chybi_denik"] and motor["nalet_min"] > 0
    assert {t["nazev"] for t in motor["terminy"]} >= {"ARC", "Pojištění", "100h prohlídka"}
    assert {t["nazev"] for t in letadla["OK-T101"]["terminy"]} >= {"Roční prohlídka"}
    stavy = {t["stav"] for let in letadla.values() for t in let["terminy"]}
    assert stavy == {"ok", "pozor", "chyba"}  # pestrá data

    pocet = TerminLetadla.objects.count()
    call_command("testovaci_letadla")  # bez --prepsat nic nového
    assert TerminLetadla.objects.count() == pocet
    call_command("testovaci_letadla", prepsat=True)
    assert TerminLetadla.objects.count() == pocet


def test_prehled_ukazuje_i_testovaci_osoby(jako, spravce):
    testovaci = osoba("Testovací", testovaci=True)
    Opravneni.objects.create(osoba=testovaci, kategorie="kluzak", uroven="pilot")
    piloti = jako(spravce).get("/api/sprava/piloti").json()
    assert [p["testovaci"] for p in piloti if p["id"] == testovaci.pk] == [True]
