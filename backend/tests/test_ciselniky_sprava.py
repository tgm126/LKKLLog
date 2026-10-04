import pytest

from ciselniky.models import DruhPrukazu, KvalifikacePrukazu, ProvozniOpravneni
from osoby.models import Osoba

from .pomocne import post

pytestmark = pytest.mark.django_db
URL = "/api/sprava/ciselniky"


@pytest.fixture
def admin(db):
    return Osoba.objects.create_superuser("admin@example.com", "x")


def test_jen_admin(jako, svet):
    assert jako(svet.pilot).get(URL).status_code == 403
    assert jako(svet.casomeric).get(f"{URL}/druhy-prukazu").status_code == 403


def test_vychozi_hodnoty_a_hierarchie(jako, admin):
    klient = jako(admin)
    prehled = {c["klic"]: c for c in klient.get(URL).json()}
    assert prehled["druhy-prukazu"]["pocet"] == 9 and prehled["kvalifikace"]["rodic"]

    druhy = klient.get(f"{URL}/druhy-prukazu").json()
    assert druhy["deti"] == "kvalifikace"
    spl = next(r for r in druhy["radky"] if r["hodnoty"]["nazev"] == "SPL")
    assert spl["systemova"] and spl["hodnoty"]["kategorie"] == ["kluzak", "tmg"]

    kvalifikace = klient.get(f"{URL}/kvalifikace?rodic={spl['id']}").json()
    nazvy = [r["hodnoty"]["nazev"] for r in kvalifikace["radky"]]
    assert nazvy[:2] == ["Naviják / auto", "Aerovlek"]


def test_pridat_upravit_smazat(jako, admin):
    klient = jako(admin)
    data = {"hodnoty": {"nazev": "Vlekař instruktor", "aktivni": True, "poradi": 50}}
    radky = post(klient, f"{URL}/provozni-opravneni", data).json()["radky"]
    nova = next(r for r in radky if r["hodnoty"]["nazev"] == "Vlekař instruktor")
    assert not nova["systemova"]

    zmena = {"id": nova["id"], "hodnoty": {"nazev": "Instruktor vlekařů"}}
    post(klient, f"{URL}/provozni-opravneni", zmena)
    assert ProvozniOpravneni.objects.get(pk=nova["id"]).nazev == "Instruktor vlekařů"

    assert post(klient, f"{URL}/provozni-opravneni", data | {"id": None}).status_code == 200
    duplicita = post(klient, f"{URL}/provozni-opravneni", data)
    assert duplicita.status_code == 400  # stejný název podruhé

    post(klient, f"{URL}/provozni-opravneni/{nova['id']}/smazat")
    assert not ProvozniOpravneni.objects.filter(pk=nova["id"]).exists()

    systemova = ProvozniOpravneni.objects.get(kod="navijakar")
    odpoved = post(klient, f"{URL}/provozni-opravneni/{systemova.pk}/smazat")
    assert odpoved.status_code == 400 and "deaktivovat" in odpoved.json()["detail"]


def test_podrizena_polozka_a_kontrola_hodnot(jako, admin):
    klient = jako(admin)
    spl = DruhPrukazu.objects.get(kod="spl")
    hodnoty = {"nazev": "Navijákový start do 600 m", "kategorie": ["kluzak"]}
    nova = {"rodic": spl.pk, "hodnoty": hodnoty}
    assert post(klient, f"{URL}/kvalifikace", nova).status_code == 200
    assert KvalifikacePrukazu.objects.filter(druh=spl, nazev__startswith="Navijákový").exists()

    bez_rodice = {"hodnoty": {"nazev": "Něco"}}
    assert post(klient, f"{URL}/kvalifikace", bez_rodice).status_code == 400
    spatna_kategorie = {"rodic": spl.pk, "hodnoty": {"nazev": "X", "kategorie": ["raketa"]}}
    assert post(klient, f"{URL}/kvalifikace", spatna_kategorie).status_code == 400
    typ = {"hodnoty": {"nazev": "L-13 Blaník", "kategorie": "vzducholod"}}
    assert post(klient, f"{URL}/typy-letadel", typ).status_code == 400

    # Letiště bez ICAO se uloží s prázdným (NULL) kódem – víc takových nevadí.
    for nazev in ("Plocha A", "Plocha B"):
        letiste = {"hodnoty": {"icao": "", "nazev": nazev, "teren": True}}
        assert post(klient, f"{URL}/letiste", letiste).status_code == 200
