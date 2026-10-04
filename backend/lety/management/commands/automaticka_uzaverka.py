"""Automatická denní uzávěrka po soumraku. Spouští ji cron serveru (server/udrzba.sh)."""

from django.core.management.base import BaseCommand

from lety.uzaverky import uzavrit_automaticky


class Command(BaseCommand):
    help = "Uzavře dny, kdy se létalo, pokud po soumraku nic neletí ani není připravené."

    def handle(self, *args, **options):
        # Při úspěchu nic nevypisuje (cron by výstup poslal e-mailem); -v 2 vypíše dny.
        for u in uzavrit_automaticky():
            if options["verbosity"] > 1:
                self.stdout.write(f"Uzavřen den {u.obdobi:%d.%m.%Y}")
