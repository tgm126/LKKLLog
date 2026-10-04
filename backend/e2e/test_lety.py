import re

from playwright.sync_api import expect

from lety.models import Let, StavLetu

from .conftest import let_pilota, prihlasit


def vybrat(stranka, pole: str, volba: str) -> None:
    stranka.get_by_role("combobox", name=pole).click()
    stranka.get_by_role("option", name=volba).click()


def test_cely_let_na_mobilu(mobil, svet):
    """Časoměřič založí let, odstartuje ho a zapíše přistání – vše ťukáním."""
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="+ NOVÝ LET").click()
    expect(mobil.get_by_text("Krok 1/5: Letadlo")).to_be_visible()
    mobil.get_by_role("button", name=re.compile("^OK-TCS")).click()
    mobil.get_by_role("button", name="Normální").click()
    vybrat(mobil, "PIC", "Pilot Adam")
    expect(mobil.get_by_role("combobox", name="Platí")).to_have_value("Pilot Adam")
    mobil.get_by_role("button", name="Dál").click()
    vybrat(mobil, "Úloha", "LP – Let do prostoru")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="VZLET TEĎ").click()

    expect(mobil.get_by_text("Ve vzduchu (1)")).to_be_visible()
    expect(mobil.get_by_text("Adam Pilot (PIC)")).to_be_visible()

    mobil.get_by_role("button", name="PŘISTÁL").click()
    mobil.get_by_role("button", name="Potvrdit přistání").click()
    # Let trval pár sekund → aplikace se zeptá, jak ho brát.
    mobil.get_by_role("button", name="Normální let (skutečný čas)").click()
    expect(mobil.get_by_text("Ukončené (1)")).to_be_visible()
    assert Let.objects.get().stav == StavLetu.UKONCEN


def test_zpet_po_omylem_zapsanem_pristani(mobil, svet):
    let_pilota(svet)
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="PŘISTÁL").click()
    mobil.get_by_role("button", name="Potvrdit přistání").click()
    expect(mobil.get_by_text("Ukončené (1)")).to_be_visible()

    mobil.locator(".mantine-Notification-root").get_by_role("button", name="Zpět").click()
    expect(mobil.get_by_text("Ve vzduchu (1)")).to_be_visible()


def test_touch_and_go_behem_letu(mobil, svet):
    let_pilota(svet)
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="T&G").click()
    expect(mobil.get_by_text("T&G 1 · naposledy")).to_be_visible()

    mobil.get_by_role("button", name="PŘISTÁL").click()
    expect(mobil.get_by_role("dialog").get_by_text("Zapsáno během letu")).to_be_visible()
    mobil.get_by_role("button", name="Potvrdit přistání").click()
    expect(mobil.get_by_text("Ukončené (1)")).to_be_visible()
    expect(mobil.get_by_text("přistání 2")).to_be_visible()
    assert Let.objects.get().pocet_pristani == 2


def test_oprava_s_duvodem_a_historie(mobil, svet):
    let_pilota(svet, stav=StavLetu.UKONCEN, minut=60)
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_text("OK-TCS", exact=True).click()
    mobil.get_by_role("button", name="Opravit…").click()
    mobil.get_by_role("button", name="Touch-and-go: více").click()
    mobil.get_by_role("button", name="Touch-and-go: více").click()
    expect(mobil.get_by_role("button", name="Uložit opravu")).to_be_disabled()
    vybrat(mobil, "Důvod opravy", "Zapomenutý stop")
    mobil.get_by_role("button", name="Uložit opravu").click()
    expect(mobil.get_by_text("přistání 3")).to_be_visible()

    mobil.get_by_text("OK-TCS", exact=True).click()
    dialog = mobil.get_by_role("dialog")
    expect(dialog.get_by_text("Oprava · Eva Časoměřič")).to_be_visible()
    expect(dialog.get_by_text("Zapomenutý stop")).to_be_visible()
    expect(dialog.get_by_text("touch-and-go:")).to_be_visible()


def test_pilot_neovlada_cizi_let(mobil, svet):
    let_pilota(svet)
    prihlasit(mobil, svet, "ivan@example.com")
    expect(mobil.get_by_text("Adam Pilot (PIC)")).to_be_visible()
    expect(mobil.get_by_role("button", name="PŘISTÁL")).to_have_count(0)


def test_letici_pilot_nemuze_vzletnout_znovu(mobil, svet):
    let_pilota(svet)
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="+ NOVÝ LET").click()
    mobil.get_by_role("button", name=re.compile("^OK-TVA")).click()
    mobil.get_by_role("button", name="Normální").click()
    vybrat(mobil, "PIC", "Pilot Adam – ✈ ve vzduchu")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="VZLET TEĎ").click()
    expect(mobil.get_by_text("Adam Pilot je právě ve vzduchu na OK-TCS")).to_be_visible()


def test_vlek_dvojice_startuje_spolecne(mobil, svet):
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="+ NOVÝ LET").click()
    mobil.get_by_role("button", name=re.compile("^OK-T101")).click()
    mobil.get_by_role("button", name="Normální").click()
    vybrat(mobil, "PIC", "Pilot Adam")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_text("Vlek", exact=True).click()
    expect(mobil.get_by_role("button", name="Dál")).to_be_disabled()
    vybrat(mobil, "Vlečné letadlo", "OK-TZL (Zlin vlečný)")
    vybrat(mobil, "Vlekař", "Vlekař Gustav")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="Připravit (vzlet zmáčknu později)").click()

    expect(mobil.get_by_text("Připravené (2)")).to_be_visible()
    mobil.get_by_role("button", name="VZLET").first.click()
    expect(mobil.get_by_text("Ve vzduchu (2)")).to_be_visible()
    expect(mobil.get_by_text("⇄ vlek OK-TZL (Gustav Vlekař)")).to_be_visible()
    expect(mobil.get_by_text("⇄ vleče OK-T101 (Adam Pilot)")).to_be_visible()


def test_dalsi_let_odsud_s_prohozenim_roli(mobil, svet):
    """Dva členové letí tam a zpátky a na zpáteční cestě si prohodí role."""
    let = let_pilota(svet, stav=StavLetu.UKONCEN, minut=60)
    let.posadka.create(osoba=svet.jiny_pilot, funkce="clen")
    let.misto_pristani = svet.letnany
    let.save()
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="Další akce").click()
    mobil.get_by_role("menuitem", name="Další let odsud…").click()
    expect(mobil.get_by_text("Krok 3/5: Posádka")).to_be_visible()
    mobil.get_by_role("button", name="⇅ Prohodit role (PIC ↔ člen)").click()
    expect(mobil.get_by_role("combobox", name="PIC")).to_have_value("Pilot Ivan")
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="Dál").click()
    mobil.get_by_role("button", name="VZLET TEĎ").click()

    expect(mobil.get_by_text("Ve vzduchu (1)")).to_be_visible()
    novy = Let.objects.get(stav=StavLetu.VE_VZDUCHU)
    assert novy.misto_vzletu == svet.letnany
    assert novy.letadlo == let.letadlo
    posadka = dict(novy.posadka.values_list("osoba_id", "funkce"))
    assert posadka == {svet.jiny_pilot.pk: "pic", svet.pilot.pk: "clen"}
    assert novy.platce == svet.jiny_pilot


def test_nabidka_jen_doporucenych_a_ostatni_na_pozadani(mobil, svet):
    prihlasit(mobil, svet, "casomeric@example.com")
    mobil.get_by_role("button", name="+ NOVÝ LET").click()
    mobil.get_by_role("button", name=re.compile("^OK-TZL")).click()
    mobil.get_by_role("button", name="Normální").click()
    # Na motorovém letadle se nabízejí jen piloti s motorovým oprávněním, ne žák.
    mobil.get_by_role("combobox", name="PIC").click()
    expect(mobil.get_by_role("option", name="Pilot Adam")).to_be_visible()
    expect(mobil.get_by_role("option", name="Žák Bára")).to_have_count(0)
    mobil.keyboard.press("Escape")
    mobil.get_by_role("button", name=re.compile("Ukázat i ostatní")).click()
    vybrat(mobil, "PIC", "Žák Bára")
    expect(mobil.get_by_role("combobox", name="PIC")).to_have_value("Žák Bára")
