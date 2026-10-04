import re

from django.core import mail
from playwright.sync_api import expect

from .conftest import HESLO, prihlasit


def test_spatne_a_spravne_heslo(page, svet):
    page.goto(svet.url)
    expect(page.get_by_text("TESTOVACÍ PROVOZ")).to_be_visible()
    page.get_by_role("textbox", name="E-mail").fill("pilot@example.com")
    page.locator("input[type=password]").fill("spatne-heslo")
    page.get_by_role("button", name="Přihlásit se").click()
    expect(page.get_by_text("Nesprávný e-mail nebo heslo.")).to_be_visible()

    page.locator("input[type=password]").fill(HESLO)
    page.get_by_role("button", name="Přihlásit se").click()
    expect(page.get_by_text("Ve vzduchu (0)")).to_be_visible()
    page.get_by_role("button", name="Adam").click()
    page.get_by_role("menuitem", name="Odhlásit se").click()
    expect(page.get_by_role("button", name="Přihlásit se")).to_be_visible()


def test_zapomenute_heslo(page, svet):
    page.goto(svet.url)
    page.get_by_role("link", name="Zapomenuté heslo").click()
    # Počkat, až se místo přihlášení zobrazí nový formulář (jinak by se vyplnil starý).
    expect(page.get_by_role("heading", name="Zapomenuté heslo")).to_be_visible()
    page.get_by_role("textbox", name="E-mail").fill("zak@example.com")
    page.get_by_role("button", name="Poslat odkaz").click()
    expect(page.get_by_text("Pokud je e-mail v aplikaci")).to_be_visible()

    assert len(mail.outbox) == 1
    odkaz = re.search(r"https?://\S+/nastavit-heslo/\S+", mail.outbox[0].body).group(0)
    page.goto(odkaz)
    expect(page.get_by_text("zak@example.com")).to_be_visible()
    hesla = page.locator("input[type=password]")
    hesla.nth(0).fill("Nove-Heslo-Pro-Baru-1")
    hesla.nth(1).fill("Nove-Heslo-Pro-Baru-1")
    page.get_by_role("button", name="Uložit heslo a přihlásit se").click()
    expect(page.get_by_role("button", name="Bára")).to_be_visible()


def test_prihlasit_se_jako_a_vratit_se(page, svet):
    page.goto(f"{svet.url}/admin/")
    page.get_by_label("E-mail").fill("admin@example.com")
    page.get_by_label("Heslo").fill(HESLO)
    page.locator("input[type=submit]").click()
    expect(page.get_by_text("Číselníky a správa")).to_be_visible()
    page.goto(f"{svet.url}/admin/osoby/osoba/?q=Žák")
    page.get_by_role("checkbox", name=re.compile("Žák Bára")).check()
    page.locator("select[name=action]").select_option("prihlasit_jako")
    page.locator("#changelist-form button[name=index]").click()

    expect(page.get_by_text("Jste přihlášen jako Bára Žák")).to_be_visible()
    page.get_by_role("button", name=re.compile("Vrátit se")).click()
    expect(page).to_have_url(re.compile("/admin/osoby/osoba/"))


def test_odkaz_do_administrace_jen_pro_admina(page, svet):
    prihlasit(page, svet, "pilot@example.com")
    page.get_by_role("button", name="Adam").click()
    expect(page.get_by_role("menuitem", name="Administrace")).to_have_count(0)
