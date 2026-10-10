"""Odesílání e-mailů z info@lkkl.cz (docs/modul-email.md).

SMTP se STARTTLS a přihlášením podle proměnných prostředí (nastaveni.py). Bez
LKKL_SMTP_SERVER (vývoj, testy) se nic neodešle – e-mail se jen vypíše do logu serveru.
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formatdate, make_msgid

from .nastaveni import nastaveni

log = logging.getLogger("lkkl.posta")


class ChybaPosty(Exception):
    """E-mail se nepodařilo odeslat (text chyby SMTP nebo spojení)."""


def odeslat(komu: str, predmet: str, text: str, priloha: tuple[str, bytes] | None = None) -> None:
    """`priloha`: (název souboru, obsah PDF)."""
    zprava = EmailMessage()
    zprava["From"] = nastaveni.email_od
    zprava["To"] = komu
    zprava["Subject"] = predmet
    zprava["Date"] = formatdate(usegmt=True)  # UTC jako „+0000“ („-0000“ = pásmo neznámé)
    zprava["Message-ID"] = make_msgid(domain="lkkl.cz")
    if nastaveni.email_odpoved:
        zprava["Reply-To"] = nastaveni.email_odpoved
    zprava.set_content(text)
    if priloha:
        nazev, obsah = priloha
        zprava.add_attachment(obsah, maintype="application", subtype="pdf", filename=nazev)
    if not nastaveni.smtp_server:
        if priloha:  # obsah přílohy do logu nepatří
            log.warning(
                "E-mail se neodesílá (chybí LKKL_SMTP_SERVER): komu %s, %s, příloha %s (%d B)",
                komu,
                predmet,
                priloha[0],
                len(priloha[1]),
            )
        else:
            log.warning("E-mail se neodesílá (chybí LKKL_SMTP_SERVER):\n%s", zprava)
        return
    try:
        with smtplib.SMTP(nastaveni.smtp_server, nastaveni.smtp_port, timeout=10) as smtp:
            smtp.starttls(context=ssl.create_default_context())  # ověřit certifikát
            if nastaveni.smtp_uzivatel:
                smtp.login(nastaveni.smtp_uzivatel, nastaveni.smtp_heslo)
            smtp.send_message(zprava)
    except (OSError, smtplib.SMTPException) as e:
        raise ChybaPosty(str(e) or type(e).__name__) from e
