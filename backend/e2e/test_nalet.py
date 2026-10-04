import os

from playwright.sync_api import expect

from lety.models import StavLetu

from .conftest import let_pilota, prihlasit


def test_muj_nalet(mobil, svet):
    let_pilota(svet, stav=StavLetu.UKONCEN, minut=90)
    prihlasit(mobil, svet, "pilot@example.com")
    mobil.get_by_role("link", name="Můj nálet").click()
    expect(mobil.get_by_role("heading", name="Můj nálet")).to_be_visible()
    expect(mobil.get_by_text("Podle kategorie a funkce")).to_be_visible()
    expect(mobil.get_by_role("cell", name="Motorové")).to_be_visible()
    expect(mobil.get_by_role("link", name="Stáhnout Excel")).to_be_visible()
    if cesta := os.environ.get("SNIMEK_NALETU"):  # jen pro ruční kontrolu vzhledu
        mobil.screenshot(path=cesta, full_page=True)

    mobil.get_by_role("cell", name="OK-TCS").click()
    expect(mobil.get_by_role("dialog").get_by_text("Historie změn")).to_be_visible()
