import os

from playwright.sync_api import expect

from lety.models import TerminLetadla
from osoby.models import Osoba

from .conftest import HESLO, prihlasit


def test_spravce_piloti_a_letadla(mobil, svet):
    Osoba.objects.create_user(
        "spravce@example.com", HESLO, jmeno="Sára", prijmeni="Správcová", role_spravce=True
    )
    snimky = os.environ.get("SNIMKY_SPRAVY")
    prihlasit(mobil, svet, "spravce@example.com")

    mobil.get_by_role("link", name="Piloti a letadla").click()
    expect(mobil.get_by_role("heading", name="Piloti a letadla")).to_be_visible()
    expect(mobil.get_by_text("Medical: Není zadaný.").first).to_be_visible()
    if snimky:
        mobil.screenshot(path=f"{snimky}/sprava-piloti.png", full_page=True)

    # Detail pilota → úprava jeho licencí a medicalu.
    mobil.get_by_text("Adam Pilot", exact=True).click()
    mobil.get_by_role("link", name="Upravit licence a medical").click()
    expect(mobil.get_by_role("heading", name="Licence a medical – Adam Pilot")).to_be_visible()
    mobil.get_by_role("button", name="+ Zadat medical").click()
    mobil.get_by_label("Třída 2 – platí do").fill("2027-06-30")
    mobil.get_by_label("LAPL – platí do").fill("2030-06-30")
    mobil.get_by_role("dialog").get_by_role("button", name="Uložit").click()
    expect(mobil.get_by_text("Třída 2 do 30. 6. 2027")).to_be_visible()
    assert svet.pilot.medicaly.count() == 2

    # Letadla: nový termín.
    mobil.get_by_role("link", name="← Piloti a letadla").click()
    expect(mobil.get_by_role("heading", name="Piloti a letadla")).to_be_visible()
    mobil.get_by_text("Letadla", exact=True).click()
    mobil.get_by_role("button", name="+ Termín").first.click()
    dialog = mobil.get_by_role("dialog")
    dialog.get_by_label("Název").fill("ARC")
    dialog.get_by_label("Do data").fill("2027-03-31")
    dialog.get_by_role("button", name="Uložit").click()
    expect(mobil.get_by_text("do 31. 3. 2027", exact=False)).to_be_visible()
    assert TerminLetadla.objects.get().nazev == "ARC"
    if snimky:
        mobil.screenshot(path=f"{snimky}/sprava-letadla.png", full_page=True)


def test_pilot_spravu_nevidi(mobil, svet):
    prihlasit(mobil, svet, "pilot@example.com")
    expect(mobil.get_by_role("link", name="Piloti a letadla")).to_have_count(0)
