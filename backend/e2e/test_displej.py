from datetime import timedelta

from django.utils import timezone
from playwright.sync_api import expect

from lety.models import Let, StavLetu, Ucel
from provoz.models import Nastaveni

from .conftest import let_pilota


def test_displej_bez_prihlaseni(page, svet):
    let_pilota(svet)
    vzlet = timezone.now().replace(microsecond=0) - timedelta(minutes=50)
    ukonceny = Let.objects.create(
        letadlo=svet.zlin,
        ucel=Ucel.NORMALNI,
        misto_vzletu=svet.lkkl,
        misto_pristani=svet.lkkl,
        platce=svet.jiny_pilot,
        zalozil=svet.jiny_pilot,
        stav=StavLetu.UKONCEN,
        cas_vzletu=vzlet,
        cas_pristani=vzlet + timedelta(minutes=30),
        pocet_tg=2,
    )
    ukonceny.posadka.create(osoba=svet.jiny_pilot, funkce="pic")
    nastaveni = Nastaveni.aktualni()
    klic = nastaveni.novy_klic_displeje()
    nastaveni.save()

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{svet.url}/displej/{klic}")
    expect(page.get_by_text("Ve vzduchu (1)")).to_be_visible()
    expect(page.get_by_text("OK-TCS")).to_be_visible()
    expect(page.get_by_text("Adam Pilot (PIC)")).to_be_visible()
    expect(page.get_by_text("Konec soumraku")).to_be_visible()
    # U letadla je vidět počet letů i přistání (T&G se počítají do přistání).
    expect(page.get_by_text("Přistání vč. T&G")).to_be_visible()
    expect(page.get_by_text('1 let · 3 přist. · 30"')).to_be_visible()
    # Displej nemá ovládání ani přihlašovací formulář.
    expect(page.get_by_role("button")).to_have_count(0)

    page.goto(f"{svet.url}/displej/neplatny")
    expect(page.get_by_text("Odkaz na displej neplatí")).to_be_visible()
