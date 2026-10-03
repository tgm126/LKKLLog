from django.core.management.base import BaseCommand

from lety.ciselniky import vytvor_sablonu


class Command(BaseCommand):
    help = "Vytvoří prázdnou excelovou šablonu pro úvodní načtení číselníků."

    def add_arguments(self, parser):
        parser.add_argument("soubor", nargs="?", default="ciselniky.xlsx")

    def handle(self, *args, soubor, **options):
        vytvor_sablonu(soubor)
        self.stdout.write(self.style.SUCCESS(f"Šablona uložena do {soubor}"))
