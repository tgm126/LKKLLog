import pytest

from lety.models import Letadlo, Letiste, Osnova, Ucel, Uloha
from osoby.models import Kategorie, Osoba

from .pomocne import osoba


@pytest.fixture
def pilot(db):
    return Osoba.objects.create_user(
        "novak@example.com", "tajne-heslo-123", jmeno="Jan", prijmeni="Novák"
    )


@pytest.fixture
def kluzak(db):
    return Letadlo.objects.create(
        imatrikulace="OK-0815", typ="L-13 Blaník", kategorie=Kategorie.KLUZAK, pocet_mist=2
    )


@pytest.fixture
def lkkl(db):
    return Letiste.objects.create(icao="LKKL", nazev="Kladno", domovske=True)


@pytest.fixture(autouse=True)
def bez_manifestu_statickych_souboru(settings):
    # V testech nejsou statické soubory sebrané (collectstatic běží až v Docker image).
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


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
    s.ucetni = osoba("Účetní", role_ucetni=True)
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
