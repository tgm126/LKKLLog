from playwright.sync_api import expect

from lety.models import StavLetu

from .conftest import let_pilota, prihlasit


def test_casomeric_uzavre_den_a_pilot_uz_jen_cte(mobil, browser, svet):
    let_pilota(svet, stav=StavLetu.UKONCEN, minut=20)
    prihlasit(mobil, svet, "casomeric@example.com")

    mobil.get_by_role("button", name="Uzavřít den").click()
    dialog = mobil.get_by_role("dialog")
    expect(dialog.get_by_text("Uzavíráte dnešek")).to_be_visible()
    expect(dialog.get_by_role("cell", name="OK-TCS")).to_be_visible()
    dialog.get_by_role("button", name="Uzavřít den").click()
    expect(mobil.get_by_text("den uzavřen v1")).to_be_visible()

    # Obrazovka Uzávěrky ukazuje den jako uzavřený.
    mobil.get_by_role("link", name="Uzávěrky").click()
    expect(mobil.get_by_text("Měsíční uzávěrka")).to_be_visible()
    expect(mobil.get_by_text("uzavřeno v1")).to_be_visible()

    # Pilot svůj let v uzavřeném dni už neopraví (nemá nabídku akcí).
    kontext = browser.new_context(viewport={"width": 390, "height": 844}, locale="cs-CZ")
    pilot = kontext.new_page()
    prihlasit(pilot, svet, "pilot@example.com")
    expect(pilot.get_by_text("den uzavřen v1")).to_be_visible()
    expect(pilot.get_by_text("OK-TCS")).to_be_visible()
    expect(pilot.get_by_role("button", name="Další akce")).to_have_count(0)
    expect(pilot.get_by_role("link", name="Uzávěrky")).to_have_count(0)
    kontext.close()
