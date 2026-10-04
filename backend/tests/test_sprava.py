from datetime import UTC, datetime, time, timedelta

import pytest
from django.utils import timezone

from ciselniky.models import DruhPrukazu, KvalifikacePrukazu, ProvozniOpravneni
from lety.models import TerminLetadla
from osoby.models import KvalifikaceOsoby, Osoba, PrukazOsoby, Vycvik

from .pomocne import let_v, osoba, post, prukaz, typ_letadla

pytestmark = pytest.mark.django_db

DNES = timezone.now().date()


@pytest.fixture
def spravce(svet):
    return osoba("Správce", role_spravce=True)


def kval(druh_kod, kod):
    return KvalifikacePrukazu.objects.get(druh__kod=druh_kod, kod=kod).pk


def druh(kod):
    return DruhPrukazu.objects.get(kod=kod).pk


def karta_pilota(**zmeny):
    """Data karty: SPL s navijákem, medical třída 2 a LAPL, navijákář."""
    data = {
        "jmeno": "Test",
        "prijmeni": "Pilot",
        "prukazy": [
            {
                "druh_id": druh("spl"),
                "cislo": "CZ.SFCL.1",
                "kvalifikace": [{"kvalifikace_id": kval("spl", "navijak")}],
            },
            {
                "druh_id": druh("medical"),
                "kvalifikace": [
                    {"kvalifikace_id": kval("medical", "t2"), "platnost_do": "2027-03-31"},
                    {"kvalifikace_id": kval("medical", "lapl"), "platnost_do": "2029-03-31"},
                ],
            },
        ],
        "provozni": [ProvozniOpravneni.objects.get(kod="navijakar").pk],
    }
    data.update(zmeny)
    return data


def test_seznam_osob_jen_pro_spravce(jako, svet, spravce):
    prukaz(svet.pilot, "spl", ("navijak", None))
    assert jako(svet.pilot).get("/api/sprava/osoby").status_code == 403
    osoby = {o["id"]: o for o in jako(spravce).get("/api/sprava/osoby").json()}
    pilot = osoby[svet.pilot.pk]
    assert pilot["prukazy"] == ["SPL"] and pilot["stav"] == "chyba"
    assert "Medical: Není zadaný." in pilot["problemy"]
    assert osoby[svet.ucetni.pk]["stav"] == ""  # nelétá – stav se nepočítá
    assert osoby[spravce.pk]["role"] == ["správce"]


def test_karta_osoby_ulozi_doklady_a_opravneni(jako, svet, spravce):
    kluzak = typ_letadla(svet.kluzak)
    klient = jako(spravce)
    karta = post(klient, f"/api/sprava/osoby/{svet.pilot.pk}", karta_pilota(preskoleni=[kluzak.pk]))
    data = karta.json()
    assert karta.status_code == 200, data
    assert [p["cislo"] for p in data["prukazy"]] == ["CZ.SFCL.1", ""]
    assert data["preskoleni"] == [kluzak.pk] and len(data["provozni"]) == 1
    medical = KvalifikaceOsoby.objects.filter(prukaz__druh__kod="medical", prukaz__osoba=svet.pilot)
    assert medical.count() == 2
    assert any(k["nazev"] == "Medical" and k["stav"] == "ok" for k in data["kontroly"])

    # Uložení bez medicalu průkaz odebere.
    bez = karta_pilota()
    bez["prukazy"] = bez["prukazy"][:1]
    post(klient, f"/api/sprava/osoby/{svet.pilot.pk}", bez)
    assert not PrukazOsoby.objects.filter(osoba=svet.pilot, druh__kod="medical").exists()

    spatne = karta_pilota()
    spatne["prukazy"][0]["kvalifikace"] = [{"kvalifikace_id": kval("ppl_a", "sep")}]
    assert post(klient, f"/api/sprava/osoby/{svet.pilot.pk}", spatne).status_code == 400
    dvakrat = karta_pilota()
    dvakrat["prukazy"].append(dvakrat["prukazy"][0])
    assert post(klient, f"/api/sprava/osoby/{svet.pilot.pk}", dvakrat).status_code == 400


def test_role_meni_jen_admin(jako, svet, spravce):
    s_rolemi = karta_pilota(role={"casomeric": True, "admin": True})
    post(jako(spravce), f"/api/sprava/osoby/{svet.pilot.pk}", s_rolemi)
    svet.pilot.refresh_from_db()
    assert not svet.pilot.role_casomeric and not svet.pilot.is_staff
    admin = Osoba.objects.create_superuser("admin@example.com", "x")
    post(jako(admin), f"/api/sprava/osoby/{svet.pilot.pk}", s_rolemi)
    svet.pilot.refresh_from_db()
    assert svet.pilot.role_casomeric and svet.pilot.is_staff


def test_nova_osoba_a_telefon_na_vyzadani(jako, svet, spravce):
    klient = jako(spravce)
    data = karta_pilota(jmeno="Nová", prijmeni="Pilotka", email="nova@example.com")
    data["telefon"] = "731 123 456"
    karta = post(klient, "/api/sprava/osoby", data).json()
    assert karta["ma_telefon"] and "telefon" not in karta  # telefon jen na vyžádání
    telefon = klient.get(f"/api/sprava/osoby/{karta['id']}/telefon").json()
    assert telefon == {"telefon": "+420731123456"}
    stejny_email = karta_pilota(jmeno="Jiná", email="nova@example.com")
    assert post(klient, "/api/sprava/osoby", stejny_email).status_code == 400


def test_zak_bez_licence_neni_chyba(jako, svet, spravce):
    Vycvik.objects.create(osoba=svet.zak, druh_id=druh("spl"))
    karta = jako(spravce).get(f"/api/sprava/osoby/{svet.zak.pk}").json()
    licence = next(k for k in karta["kontroly"] if k["nazev"] == "Licence")
    assert licence["stav"] == "info"


def test_nabidky_v_pruvodci_podle_dokladu(jako, svet):
    """Kdo se hodí do které role: průkaz, instruktor, výcvik, vlekání, přeškolení."""
    kluzak = typ_letadla(svet.kluzak)
    prukaz(svet.pilot, "ppl_a", ("sep", None), ("vlekani", None))
    prukaz(svet.instruktor, "instruktor", ("fi_s_omezeny", None))
    prukaz(svet.instruktor, "spl", ("navijak", None))
    svet.instruktor.preskoleni.create(typ=kluzak)
    Vycvik.objects.create(osoba=svet.zak, druh_id=druh("spl"))
    osoby = {o["id"]: o for o in jako(svet.casomeric).get("/api/ciselniky").json()["osoby"]}
    assert osoby[svet.pilot.pk]["pilot"] == ["motor"]
    assert osoby[svet.pilot.pk]["vlekar"] == ["motor", "tmg"]
    instruktor = osoby[svet.instruktor.pk]
    assert instruktor["instruktor"] == ["kluzak"] and instruktor["dozor"] == []  # omezený
    assert instruktor["pilot"] == ["kluzak"] and instruktor["typy"] == [kluzak.pk]
    assert osoby[svet.zak.pk]["zak"] == ["kluzak", "tmg"]


def druh_terminu(nazev):
    from ciselniky.models import DruhTerminu

    return DruhTerminu.objects.get(nazev=nazev).pk


def karta_letadla(letadlo, **zmeny):
    return {
        "imatrikulace": letadlo.imatrikulace,
        "typ_letadla_id": typ_letadla(letadlo).pk,
        "pocet_mist": letadlo.pocet_mist,
        "vlecne": letadlo.vlecne,
        **zmeny,
    }


def test_karta_letadla_nalet_z_deniku_a_terminy(jako, svet, spravce):
    vcera = datetime.combine(DNES - timedelta(days=1), time(10), tzinfo=UTC)
    let_v(svet, vcera - timedelta(days=10), minut=50)  # před stavem deníku – nepočítá se
    let_v(svet, vcera, minut=40)
    klient = jako(spravce)
    url = f"/api/sprava/letadla/{svet.motor.pk}"
    data = karta_letadla(
        svet.motor,
        nalet_pocatek_min=1199 * 60,
        starty_pocatek=3000,
        stav_k=str(DNES - timedelta(days=5)),
        terminy=[
            {"druh_id": druh_terminu("100h prohlídka"), "pri_naletu_h": 1200},
            {"druh_id": druh_terminu("ARC"), "datum": str(DNES - timedelta(days=1))},
        ],
    )
    motor = post(klient, url, data).json()
    assert motor["nalet_min"] == 1199 * 60 + 40 and motor["starty"] == 3001
    terminy = {t["nazev"]: t for t in motor["terminy"]}
    assert terminy["100h prohlídka"]["stav"] == "pozor"
    assert terminy["100h prohlídka"]["text"] == 'při 1200 h – zbývá 20"'
    assert terminy["ARC"]["stav"] == "chyba"

    # Termín bez data i náletu ani neznámý typ neprojdou.
    bez = {**data, "terminy": [{"druh_id": druh_terminu("ARC")}]}
    assert post(klient, url, bez).status_code == 400
    assert post(klient, url, {**data, "typ_letadla_id": 999999}).status_code == 400

    # Uložení karty nahradí termíny; typ z číselníku určuje typ a kategorii.
    motor = post(klient, url, {**data, "terminy": data["terminy"][:1]}).json()
    assert [t["nazev"] for t in motor["terminy"]] == ["100h prohlídka"]
    assert TerminLetadla.objects.count() == 1
    assert motor["typ"] == svet.motor.typ and motor["kategorie"] == svet.motor.kategorie
    # Pilot letadla nespravuje (až na konci – klient je sdílený).
    assert jako(svet.pilot).get("/api/sprava/letadla").status_code == 403
    assert post(jako(svet.pilot), url, data).status_code == 403


def test_nove_letadlo_a_volby(jako, svet, spravce):
    from ciselniky.models import TypLetadla

    klient = jako(spravce)
    volby = klient.get("/api/sprava/letadla/volby").json()
    assert "ARC" in {d["nazev"] for d in volby["druhy_terminu"]}
    typ = TypLetadla.objects.create(nazev="Dynamic", kategorie="ul")
    nove = post(
        klient, "/api/sprava/letadla", {"imatrikulace": " ok-u123 ", "typ_letadla_id": typ.pk}
    ).json()
    assert nove["imatrikulace"] == "OK-U123" and nove["kategorie"] == "ul"
    assert nove["chybi_denik"]
    znovu = {"imatrikulace": "OK-U123", "typ_letadla_id": typ.pk}
    assert post(klient, "/api/sprava/letadla", znovu).status_code == 400
    # Neaktivní letadla jen na vyžádání.
    post(klient, f"/api/sprava/letadla/{nove['id']}", {**znovu, "aktivni": False})
    assert nove["id"] not in {x["id"] for x in klient.get("/api/sprava/letadla").json()}
    vse = klient.get("/api/sprava/letadla?vse=true").json()
    assert nove["id"] in {x["id"] for x in vse}


def test_testovaci_doklady(svet):
    from django.core.management import call_command

    from ciselniky.models import TypLetadla

    motor = TypLetadla.objects.create(nazev="Cessna", kategorie="motor")
    kluzak = TypLetadla.objects.create(nazev="Blaník", kategorie="kluzak")
    pilot = osoba("Testovací pilot", testovaci=True)
    pilot.preskoleni.create(typ=motor)
    pilot.preskoleni.create(typ=kluzak)
    prukaz(pilot, "instruktor", ("fi_s", None))  # osvědčení instruktora zůstává
    zak = osoba("Testovací žák", testovaci=True)
    Vycvik.objects.create(osoba=zak, druh_id=druh("spl"))

    call_command("testovaci_licence")
    typy = set(PrukazOsoby.objects.filter(osoba=pilot).values_list("druh__kod", flat=True))
    assert {"spl", "medical", "instruktor"} <= typy and typy & {"ppl_a", "lapl_a"}
    # Žák: bez pilotního průkazu, ale s medicalem a radiofonním průkazem (kvůli sólu).
    zakovy = set(PrukazOsoby.objects.filter(osoba=zak).values_list("druh__kod", flat=True))
    assert zakovy == {"medical", "radio"}
    assert not PrukazOsoby.objects.filter(osoba=svet.pilot).exists()  # skutečné osoby ne

    pocet = PrukazOsoby.objects.count()
    call_command("testovaci_licence")  # bez --prepsat nic nového
    assert PrukazOsoby.objects.count() == pocet
    call_command("testovaci_licence", prepsat=True)
    assert PrukazOsoby.objects.filter(osoba=pilot, druh__kod="instruktor").exists()


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
