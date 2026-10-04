import os

from playwright.sync_api import expect

from ciselniky.models import ProvozniOpravneni

from .conftest import prihlasit


def test_admin_spravuje_ciselniky(page, svet):
    snimky = os.environ.get("SNIMKY_CISELNIKU")
    page.set_viewport_size({"width": 1280, "height": 860})
    prihlasit(page, svet, "admin@example.com")
    page.get_by_role("link", name="Číselníky").click()
    expect(page.get_by_role("heading", name="Číselníky")).to_be_visible()

    # Hierarchie: řádek průkazu ukáže jeho kvalifikace.
    page.get_by_text("Druhy průkazů", exact=True).click()
    page.get_by_role("cell", name="SPL", exact=True).click()
    expect(page.get_by_text("Kvalifikace – SPL")).to_be_visible()
    expect(page.get_by_role("cell", name="Naviják / auto")).to_be_visible()
    if snimky:
        page.screenshot(path=f"{snimky}/ciselniky-pc.png", full_page=True)

    # Nová položka v provozních oprávněních.
    page.get_by_text("Provozní oprávnění", exact=True).click()
    page.get_by_role("button", name="+ Přidat").click()
    dialog = page.get_by_role("dialog")
    dialog.get_by_label("Název").fill("Instruktor navijákářů")
    dialog.get_by_role("button", name="Uložit").click()
    expect(page.get_by_role("cell", name="Instruktor navijákářů")).to_be_visible()
    assert ProvozniOpravneni.objects.filter(nazev="Instruktor navijákářů").exists()

    if snimky:
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=f"{snimky}/ciselniky-mobil.png", full_page=True)


def test_pilot_ciselniky_nevidi(mobil, svet):
    prihlasit(mobil, svet, "pilot@example.com")
    expect(mobil.get_by_role("link", name="Číselníky")).to_have_count(0)
