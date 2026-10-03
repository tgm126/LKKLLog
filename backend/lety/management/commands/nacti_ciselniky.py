from django.core.management.base import BaseCommand, CommandError

from lety.ciselniky import ChybaNacteni, nacti


class Command(BaseCommand):
    help = "Načte číselníky z excelové šablony. Při chybě se nezmění nic."

    def add_arguments(self, parser):
        parser.add_argument("soubor")

    def handle(self, *args, soubor, **options):
        try:
            vysledek = nacti(soubor)
        except ChybaNacteni as e:
            for chyba in e.chyby:
                self.stderr.write(chyba)
            raise CommandError(f"Nic nebylo načteno, chyb: {len(e.chyby)}.") from e
        for list_ in sorted(set(vysledek.zalozeno) | set(vysledek.aktualizovano)):
            self.stdout.write(
                f"{list_}: založeno {vysledek.zalozeno.get(list_, 0)}, "
                f"aktualizováno {vysledek.aktualizovano.get(list_, 0)}"
            )
        self.stdout.write(self.style.SUCCESS("Hotovo."))
