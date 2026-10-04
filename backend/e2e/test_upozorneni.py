from playwright.sync_api import expect

from .conftest import prihlasit


def test_dialog_upozorneni_a_soubory_aplikace(mobil, svet):
    # Service worker a manifest musí server vydat z kořene webu (WhiteNoise).
    for cesta, typ in (("/sw.js", "javascript"), ("/manifest.webmanifest", "manifest")):
        odpoved = mobil.request.get(f"{svet.url}{cesta}")
        assert odpoved.ok and typ in odpoved.headers["content-type"]

    prihlasit(mobil, svet, "pilot@example.com")
    mobil.get_by_role("button", name="Adam").click()
    mobil.get_by_role("menuitem", name="Upozornění na telefon…").click()
    dialog = mobil.get_by_role("dialog")
    expect(dialog.get_by_text("je ve vzduchu déle než maximální doba letadla")).to_be_visible()
    expect(
        dialog.get_by_role("button", name="Zapnout upozornění na tomto zařízení")
    ).to_be_visible()
