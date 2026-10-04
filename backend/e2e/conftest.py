"""Klikací testy v prohlížeči (Playwright). Spuštění: `uv run pytest e2e`.

Testy běží proti živému serveru Djanga se zkušební databází; frontend musí být
sestavený (`npm run build` ve složce frontend).
"""

import os

# Playwright běží ve vlastní smyčce událostí; Django by jinak odmítlo přístup do databáze.
os.environ.setdefault("DJANGO_ALLOW_ASYNC_UNSAFE", "true")

import re  # noqa: E402
from datetime import timedelta  # noqa: E402

import pytest  # noqa: E402
from django.utils import timezone  # noqa: E402
from playwright.sync_api import Page, expect  # noqa: E402

from lety.models import Let, Letadlo, Letiste, Osnova, StavLetu, Ucel, Uloha  # noqa: E402
from osoby.models import Kategorie, Opravneni, Osoba, Uroven  # noqa: E402
from provoz.models import EmailRezim, Nastaveni  # noqa: E402

HESLO = "Zkusebni-Heslo-2026"


@pytest.fixture(autouse=True)
def _bez_manifestu(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def svet(transactional_db, live_server, settings):
    """Malý aeroklub se zkušebními účty."""
    settings.APP_URL = live_server.url
    nastaveni = Nastaveni.aktualni()
    nastaveni.email_rezim = EmailRezim.POVOLENE
    nastaveni.povolene_adresy = "*@example.com"
    nastaveni.save()

    s = type("Svet", (), {})()
    s.lkkl = Letiste.objects.create(icao="LKKL", nazev="Kladno", domovske=True)
    s.letnany = Letiste.objects.create(icao="LKLT", nazev="Letňany")
    s.cessna = Letadlo.objects.create(
        imatrikulace="OK-TCS",
        typ="Cessna 172",
        kategorie=Kategorie.MOTOR,
        pocet_mist=4,
        max_doba_min=300,
    )
    s.zlin = Letadlo.objects.create(
        imatrikulace="OK-TVA", typ="Z-226", kategorie=Kategorie.MOTOR, pocet_mist=2
    )
    s.kluzak = Letadlo.objects.create(
        imatrikulace="OK-T101", typ="L-13 Blaník", kategorie=Kategorie.KLUZAK, pocet_mist=2
    )
    s.vlecna = Letadlo.objects.create(
        imatrikulace="OK-TZL",
        typ="Zlin vlečný",
        kategorie=Kategorie.MOTOR,
        pocet_mist=2,
        vlecne=True,
    )

    def osoba(email, jmeno, prijmeni, **kw):
        return Osoba.objects.create_user(email, HESLO, jmeno=jmeno, prijmeni=prijmeni, **kw)

    s.admin = osoba("admin@example.com", "Tomáš", "Admin", is_staff=True, is_superuser=True)
    s.casomeric = osoba("casomeric@example.com", "Eva", "Časoměřič", role_casomeric=True)
    s.pilot = osoba("pilot@example.com", "Adam", "Pilot")
    s.jiny_pilot = osoba("ivan@example.com", "Ivan", "Pilot")
    s.zak = osoba("zak@example.com", "Bára", "Žák")
    s.vlekar = osoba("vlekar@example.com", "Gustav", "Vlekař")
    Opravneni.objects.create(osoba=s.vlekar, kategorie=Kategorie.MOTOR, uroven=Uroven.PILOT)
    Opravneni.objects.create(osoba=s.pilot, kategorie=Kategorie.KLUZAK, uroven=Uroven.PILOT)
    for o in (s.pilot, s.jiny_pilot):
        Opravneni.objects.create(osoba=o, kategorie=Kategorie.MOTOR, uroven=Uroven.PILOT)
    Opravneni.objects.create(osoba=s.zak, kategorie=Kategorie.MOTOR, uroven=Uroven.ZAK)
    osnova = Osnova.objects.create(kategorie=Kategorie.MOTOR, nazev="Ostatní lety")
    Uloha.objects.create(osnova=osnova, kod="LP", nazev="Let do prostoru", ucely=[Ucel.NORMALNI])
    s.url = live_server.url
    return s


def let_pilota(svet, stav=StavLetu.VE_VZDUCHU, minut=20):
    """Let Adama Pilota na OK-TCS, ve vzduchu nebo už ukončený."""
    vzlet = timezone.now().replace(microsecond=0) - timedelta(minutes=minut)
    let = Let.objects.create(
        letadlo=svet.cessna,
        ucel=Ucel.NORMALNI,
        misto_vzletu=svet.lkkl,
        platce=svet.pilot,
        zalozil=svet.casomeric,
        stav=stav,
        cas_vzletu=vzlet,
        cas_pristani=vzlet + timedelta(minutes=10) if stav == StavLetu.UKONCEN else None,
        misto_pristani=svet.lkkl if stav == StavLetu.UKONCEN else None,
    )
    let.posadka.create(osoba=svet.pilot, funkce="pic")
    return let


@pytest.fixture
def mobil(browser, svet):
    """Stránka v rozměrech telefonu s dotykovým ovládáním."""
    kontext = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True, locale="cs-CZ"
    )
    stranka = kontext.new_page()
    yield stranka
    kontext.close()


def prihlasit(stranka: Page, svet, email: str) -> None:
    stranka.goto(svet.url)
    stranka.get_by_role("textbox", name="E-mail").fill(email)
    stranka.locator("input[type=password]").fill(HESLO)
    stranka.get_by_role("button", name="Přihlásit se").click()
    # Nadpis, ne text: po soumraku karta letu píše „…stále ve vzduchu“.
    expect(stranka.get_by_role("heading", name=re.compile(r"^Ve vzduchu"))).to_be_visible()
