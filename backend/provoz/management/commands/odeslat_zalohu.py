import sys

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError

from osoby.models import Osoba

TEXT = """Dobrý den,

v příloze je týdenní export databáze aplikace LKKL Log ({nazev}, {velikost} kB).
Zálohy hostingu sahají jen 30 dní zpět, tento export je dlouhodobá kopie mimo server.

Soubor uložte na bezpečné místo – obsahuje osobní údaje členů (jména, e-maily,
telefony) a otisky hesel. Obnova databáze (na serveru jako správce):

    pg_restore --clean --if-exists -d lkkllog {nazev}

LKKL Log
"""


class Command(BaseCommand):
    help = "Pošle export databáze (ze standardního vstupu) e-mailem administrátorům."

    def add_arguments(self, parser):
        parser.add_argument("--nazev", required=True, help="Název souboru přílohy")

    def handle(self, *args, nazev, **options):
        data = sys.stdin.buffer.read()
        if not data:
            raise CommandError("Prázdný export – nic se neodeslalo.")
        adresy = list(
            Osoba.objects.filter(
                is_superuser=True, is_active=True, email__isnull=False
            ).values_list("email", flat=True)
        )
        if not adresy:
            raise CommandError("Není žádný aktivní administrátor s e-mailem.")
        zprava = EmailMessage(
            subject=f"LKKL Log – týdenní záloha databáze ({nazev})",
            body=TEXT.format(nazev=nazev, velikost=round(len(data) / 1024)),
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=adresy,
        )
        zprava.attach(nazev, data, "application/octet-stream")
        zprava.send()
        self.stdout.write(f"Záloha {nazev} odeslána: {', '.join(adresy)}")
