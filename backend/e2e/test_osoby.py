import os
import re

from playwright.sync_api import expect

from ciselniky.models import ProvozniOpravneni
from lety.models import TerminLetadla
from osoby.models import KvalifikaceOsoby, Osoba
from provoz.models import Nastaveni

from .conftest import prihlasit
from .test_lety import vybrat


def test_admin_upravi_kartu_osoby(page, svet):
    snimky = os.environ.get("SNIMKY_OSOB")
    page.set_viewport_size({"width": 1280, "height": 900})
    prihlasit(page, svet, "admin@example.com")
    page.get_by_role("link", name="Osoby").click()
    expect(page.get_by_role("heading", name="Osoby")).to_be_visible()
    expect(page.get_by_role("cell", name="Pilot Adam")).to_be_visible()
    if snimky:
        page.screenshot(path=f"{snimky}/osoby-seznam.png", full_page=True)

    page.get_by_role("cell", name="Pilot Adam").click()
    expect(page.get_by_role("heading", name="Pilot Adam")).to_be_visible()
    page.get_by_label("Třída 2", exact=True).check()
    page.get_by_label("Třída 2 platí do").fill("2027-06-30")
    page.get_by_label("Omezený (OFL)", exact=True).check()
    page.get_by_label("Omezený (OFL) platí do").fill("2034-01-31")
    page.get_by_label("Vlekání kluzáků", exact=True).check()
    page.get_by_label("Navijákář").check()
    if snimky:
        page.screenshot(path=f"{snimky}/osoby-karta.png", full_page=True)
    page.get_by_role("button", name="Uložit").first.click()
    expect(page.get_by_text("Uloženo.")).to_be_visible()

    doklady = KvalifikaceOsoby.objects.filter(prukaz__osoba=svet.pilot)
    assert doklady.get(kvalifikace__kod="t2").platnost_do.isoformat() == "2027-06-30"
    assert doklady.filter(kvalifikace__kod="vlekani").exists()
    assert svet.pilot.provozni_opravneni.get() == ProvozniOpravneni.objects.get(kod="navijakar")
    if snimky:
        page.set_viewport_size({"width": 390, "height": 844})
        page.screenshot(path=f"{snimky}/osoby-karta-mobil.png", full_page=True)


def test_nova_osoba(page, svet):
    prihlasit(page, svet, "admin@example.com")
    page.goto(f"{svet.url}/osoby/nova")
    expect(page.get_by_role("heading", name="Nová osoba")).to_be_visible()
    page.get_by_label("Jméno").fill("Nora")
    page.get_by_label("Příjmení").fill("Nováčková")
    page.get_by_role("button", name="Uložit").first.click()
    expect(page.get_by_role("heading", name="Nováčková Nora")).to_be_visible()
    assert Osoba.objects.filter(prijmeni="Nováčková").exists()


def test_varovani_v_pruvodci_letem(mobil, svet):
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_zpusobilost = nastaveni.hlidat_rozletanost = True
    nastaveni.save()
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="+ NOVÝ LET").click()
    mobil.get_by_role("button", name=re.compile("^OK-TCS")).click()
    mobil.get_by_role("button", name="Normální").click()
    vybrat(mobil, "PIC", "Pilot Adam")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="Dál").click()
    expect(mobil.get_by_text("Upozornění (let můžete přesto založit)")).to_be_visible()
    expect(mobil.get_by_text("Adam Pilot: nemá zadaný radiofonní průkaz.")).to_be_visible()
    expect(mobil.get_by_role("button", name="VZLET TEĎ")).to_be_enabled()


def test_pilot_vidi_rozletanost_ale_ne_spravu(mobil, svet):
    nastaveni = Nastaveni.aktualni()
    nastaveni.hlidat_zpusobilost = nastaveni.hlidat_rozletanost = True
    nastaveni.save()
    prihlasit(mobil, svet, "pilot@example.com")
    expect(mobil.get_by_role("link", name="Osoby")).to_have_count(0)
    mobil.get_by_role("link", name="Můj nálet").click()
    expect(mobil.get_by_role("heading", name="Licence a rozlétanost")).to_be_visible()
    expect(mobil.get_by_text("Údaje zadává admin")).to_be_visible()


def test_letadla_termin(mobil, svet):
    prihlasit(mobil, svet, "admin@example.com")
    mobil.get_by_role("link", name="Letadla").click()
    expect(mobil.get_by_role("heading", name="Letadla")).to_be_visible()
    mobil.get_by_role("button", name="+ Termín").first.click()
    dialog = mobil.get_by_role("dialog")
    dialog.get_by_label("Název").fill("ARC")
    dialog.get_by_label("Do data").fill("2027-03-31")
    dialog.get_by_role("button", name="Uložit").click()
    expect(mobil.get_by_text("do 31. 3. 2027", exact=False)).to_be_visible()
    assert TerminLetadla.objects.get().nazev == "ARC"
