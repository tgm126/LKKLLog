from playwright.sync_api import expect

from provoz.models import Nastaveni

from .conftest import let_pilota


def test_displej_bez_prihlaseni(page, svet):
    let_pilota(svet)
    nastaveni = Nastaveni.aktualni()
    klic = nastaveni.novy_klic_displeje()
    nastaveni.save()

    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(f"{svet.url}/displej/{klic}")
    expect(page.get_by_text("Ve vzduchu (1)")).to_be_visible()
    expect(page.get_by_text("OK-TCS")).to_be_visible()
    expect(page.get_by_text("Adam Pilot (PIC)")).to_be_visible()
    expect(page.get_by_text("Konec soumraku")).to_be_visible()
    # Displej nemá ovládání ani přihlašovací formulář.
    expect(page.get_by_role("button")).to_have_count(0)

    page.goto(f"{svet.url}/displej/neplatny")
    expect(page.get_by_text("Odkaz na displej neplatí")).to_be_visible()
