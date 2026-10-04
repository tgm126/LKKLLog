import os
import re

from playwright.sync_api import expect

from osoby.models import Licence
from provoz.models import Nastaveni

from .conftest import prihlasit
from .test_lety import vybrat


def test_pilot_zada_licenci_a_vidi_rozletanost(mobil, svet):
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_licence = True
    nastaveni.save()
    prihlasit(mobil, svet, "pilot@example.com")

    mobil.get_by_role("button", name="Adam").click()
    mobil.get_by_role("menuitem", name="Licence a medical").click()
    expect(mobil.get_by_role("heading", name="Licence a medical")).to_be_visible()
    mobil.get_by_role("button", name="+ Přidat licenci").click()
    dialog = mobil.get_by_role("dialog")
    vybrat(mobil, "Typ licence", "PPL(A)")
    dialog.get_by_label("SEP (land)").check()
    dialog.get_by_label("SEP (land) platí do").fill("2027-05-31")
    dialog.get_by_role("button", name="Uložit").click()
    expect(mobil.get_by_text("SEP (land) do 31. 5. 2027")).to_be_visible()
    assert Licence.objects.get().kvalifikace.get().platnost_do.isoformat() == "2027-05-31"

    mobil.get_by_role("link", name="Můj nálet").click()
    expect(mobil.get_by_role("heading", name="Licence a rozlétanost")).to_be_visible()
    expect(mobil.get_by_text("Není zadaný.").first).to_be_visible()
    expect(mobil.get_by_text("Platí do 31. 5. 2027.")).to_be_visible()
    if cesta := os.environ.get("SNIMEK_ROZLETANOSTI"):
        mobil.screenshot(path=cesta, full_page=True)


def test_varovani_v_pruvodci_letem(mobil, svet):
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_licence = True
    nastaveni.save()
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="+ NOVÝ LET").click()
    mobil.get_by_role("button", name=re.compile("^OK-TCS")).click()
    mobil.get_by_role("button", name="Normální").click()
    vybrat(mobil, "PIC", "Pilot Adam")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="Dál").click()
    expect(mobil.get_by_text("Upozornění (let můžete přesto založit)")).to_be_visible()
    text = "Adam Pilot: nemá zadanou licenci pro kategorii motorové."
    expect(mobil.get_by_text(text)).to_be_visible()
    expect(mobil.get_by_role("button", name="VZLET TEĎ")).to_be_enabled()
