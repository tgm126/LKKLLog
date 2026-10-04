"""Odesílání e-mailů. Každý e-mail aplikace jde přes `odeslat()`, které hlídá režim
odesílání z nastavení – do spuštění pro celý klub nesmí členům nic odejít."""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Nastaveni

log = logging.getLogger(__name__)


def odeslat(adresa: str, predmet: str, text: str) -> bool:
    """Odešle e-mail, pokud to režim dovolí. Vrací True, pokud byl odeslán."""
    nastaveni = Nastaveni.aktualni()
    if not nastaveni.smi_odeslat(adresa):
        log.info("E-mail pro %s neodeslán (režim %s): %s", adresa, nastaveni.email_rezim, predmet)
        return False
    send_mail(predmet, text, settings.DEFAULT_FROM_EMAIL, [adresa])
    log.info("E-mail odeslán na %s: %s", adresa, predmet)
    return True
