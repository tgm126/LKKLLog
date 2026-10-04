"""Upozornění na neukončené lety. Spouští ho cron serveru (server/udrzba.sh)."""

from django.core.management.base import BaseCommand

from lety.upozorneni import kontrola


class Command(BaseCommand):
    help = "Pošle upozornění na lety přes maximální dobu, po soumraku a neukončené z minula."

    def handle(self, *args, **options):
        # Při úspěchu nic nevypisuje (cron by výstup poslal e-mailem); -v 2 vypíše přehled.
        for u in kontrola():
            if options["verbosity"] > 1:
                self.stdout.write(f"{u}: {u.prijemci}")
