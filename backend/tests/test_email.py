"""Odkaz pro nastavení hesla e-mailem – jen admin, ručně u jedné osoby (docs/modul-email.md)."""

import dataclasses
import re
import smtplib
from urllib.parse import parse_qs, urlparse

import pytest

from app import posta, prihlasovani


class Schranka:
    """Zkušební SMTP server v paměti: co se přihlásilo a co odešlo."""

    def __init__(self):
        self.odeslane = []
        self.prihlaseni = []
        self.chyba: Exception | None = None

    def smtp(self, server, port, timeout):
        schranka = self

        class Spojeni:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def starttls(self):
                pass

            def login(self, uzivatel, heslo):
                schranka.prihlaseni.append((server, port, uzivatel, heslo))
                if schranka.chyba:
                    raise schranka.chyba

            def send_message(self, zprava):
                schranka.odeslane.append(zprava)

        return Spojeni()


@pytest.fixture
def schranka(monkeypatch):
    s = Schranka()
    nastaveni = dataclasses.replace(
        posta.nastaveni,
        smtp_server="smtp.test",
        smtp_uzivatel="info@lkkl.cz",
        smtp_heslo="tajne",
        email_odpoved="spravce@example.cz",
    )
    monkeypatch.setattr(posta, "nastaveni", nastaveni)
    monkeypatch.setattr(prihlasovani, "nastaveni", nastaveni)
    monkeypatch.setattr(posta.smtplib, "SMTP", s.smtp)
    return s


def test_odkaz_emailem(conn, osoba, prihlasit, klient, schranka):
    osoba("Admin", admin=True)
    pilot = osoba("Pilot", heslo=None)
    k = prihlasit("admin@example.cz")

    odpoved = k.post(f"/api/ucty/{pilot}/pozvanka-emailem")
    assert odpoved.status_code == 200, odpoved.text
    assert odpoved.json()["adresa"] == "pilot@example.cz"
    assert schranka.prihlaseni == [("smtp.test", 587, "info@lkkl.cz", "tajne")]
    [zprava] = schranka.odeslane
    assert zprava["To"] == "pilot@example.cz"
    assert zprava["From"] == "AK Kladno Log <info@lkkl.cz>"
    assert zprava["Reply-To"] == "spravce@example.cz"
    assert zprava["Subject"] == "AK Kladno Log – nastavení hesla"
    text = zprava.get_content()
    assert text.startswith("Dobrý den, Jan,") and "spravce@example.cz" in text

    # odkaz v e-mailu funguje
    odkaz = re.search(r"https?://\S+", text).group(0)
    klic = parse_qs(urlparse(odkaz).query)["klic"][0]
    assert (
        klient().get("/api/heslo/odkaz", params={"klic": klic}).json()["email"]
        == "pilot@example.cz"
    )

    # záznam bez obsahu, poslední e-mail v detailu osoby
    zaznam = conn.execute(
        "SELECT druh, adresa, chyba FROM lkkl.email WHERE osoba_id = %s", (pilot,)
    ).fetchall()
    assert zaznam == [{"druh": "ODKAZ_HESLO", "adresa": "pilot@example.cz", "chyba": None}]
    detail = k.get(f"/api/osoby/{pilot}").json()
    assert detail["posledni_email"]["adresa"] == "pilot@example.cz"
    assert detail["pozvanka_odeslana"] is not None

    # znovu až za 5 minut
    znovu = k.post(f"/api/ucty/{pilot}/pozvanka-emailem")
    assert znovu.status_code == 429 and len(schranka.odeslane) == 1


def test_chyba_smtp(conn, osoba, prihlasit, schranka):
    osoba("Admin", admin=True)
    pilot = osoba("Pilot")
    k = prihlasit("admin@example.cz")
    schranka.chyba = smtplib.SMTPAuthenticationError(535, b"Authentication failed")

    odpoved = k.post(f"/api/ucty/{pilot}/pozvanka-emailem")
    assert odpoved.status_code == 502
    assert odpoved.json()["detail"].startswith("E-mail se nepodařilo odeslat:")
    chyba = conn.execute("SELECT chyba FROM lkkl.email WHERE osoba_id = %s", (pilot,)).fetchone()[
        "chyba"
    ]
    assert "Authentication failed" in chyba
    # neodeslaný se do omezení nepočítá
    schranka.chyba = None
    assert k.post(f"/api/ucty/{pilot}/pozvanka-emailem").status_code == 200


def test_jen_admin(osoba, prihlasit, schranka):
    osoba("Spravce", spravuje_osoby=True)
    pilot = osoba("Pilot")
    bez_uctu = osoba("Novy", ucet=False)
    spravce = prihlasit("spravce@example.cz")
    assert spravce.post(f"/api/ucty/{pilot}/pozvanka-emailem").status_code == 403
    osoba("Admin", admin=True)
    admin = prihlasit("admin@example.cz")
    assert admin.post(f"/api/ucty/{bez_uctu}/pozvanka-emailem").status_code == 404
    assert schranka.odeslane == []


def test_bez_smtp_jen_log(osoba, prihlasit, caplog):
    osoba("Admin", admin=True)
    pilot = osoba("Pilot")
    k = prihlasit("admin@example.cz")
    with caplog.at_level("WARNING", logger="lkkl.posta"):
        assert k.post(f"/api/ucty/{pilot}/pozvanka-emailem").status_code == 200
    assert "E-mail se neodesílá" in caplog.text and "pilot@example.cz" in caplog.text
