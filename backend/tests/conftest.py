import pytest

from lety.models import Letadlo, Letiste
from osoby.models import Kategorie, Osoba


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
