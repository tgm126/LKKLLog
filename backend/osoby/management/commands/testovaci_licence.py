"""Testovací licence, medical, radiofonní průkazy a jazyková způsobilost.

Jen pro osoby s příznakem „Testovací“ (úklid před spuštěním je smaže i s licencemi).
Data jsou pestrá, aby šlo vyzkoušet všechny stavy: v pořádku, brzy vyprší, prošlé,
chybějící. Řídí se oprávněními osoby (kategorie a úroveň). Spuštění:

    uv run python manage.py testovaci_licence            # jen osoby bez licencí
    uv run python manage.py testovaci_licence --prepsat  # znovu u všech testovacích
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from osoby.models import (
    DruhKvalifikace as D,
)
from osoby.models import (
    Kategorie,
    Licence,
    Medical,
    Osoba,
    TridaMedicalu,
    TypLicence,
    Uroven,
)


def _licence(osoba):
    """Funkce, která osobě založí licenci daného typu s kvalifikacemi."""

    def zalozit(typ, *kvalifikace):
        lic = Licence.objects.create(
            osoba=osoba, typ=typ, cislo=f"TEST-{osoba.pk}-{typ}", poznamka="testovací"
        )
        for druh, platnost in kvalifikace:
            lic.kvalifikace.create(druh=druh, platnost_do=platnost)

    return zalozit


class Command(BaseCommand):
    help = "Doplní testovací licence a medical osobám s příznakem Testovací."

    def add_arguments(self, parser):
        parser.add_argument("--prepsat", action="store_true", help="Smazat a vytvořit znovu.")

    @transaction.atomic
    def handle(self, *args, prepsat=False, **options):
        dnes = timezone.now().date()
        za = lambda dni: dnes + timedelta(days=dni)  # noqa: E731
        osoby = Osoba.objects.filter(testovaci=True, externi=False, is_active=True).order_by(
            "prijmeni", "jmeno"
        )
        hotovo = 0
        for i, osoba in enumerate(osoby):
            if prepsat:
                Licence.objects.filter(osoba=osoba).delete()
                Medical.objects.filter(osoba=osoba).delete()
            elif osoba.licence.exists() or osoba.medicaly.exists():
                continue  # už má zadané údaje – nepřepisujeme
            opravneni = list(osoba.opravneni.all())
            kategorie = {o.kategorie for o in opravneni if o.uroven != Uroven.ZAK}
            jen_zak = opravneni and not kategorie

            # Medical: třída 2 a LAPL s různou platností; někdo prošlý, někdo brzy vyprší.
            if i % 5 == 0:
                medical = {TridaMedicalu.T2: za(-10), TridaMedicalu.LAPL: za(400)}
            elif i % 5 == 1:
                medical = {TridaMedicalu.T2: za(20)}
            else:
                medical = {TridaMedicalu.T2: za(300 + 50 * i), TridaMedicalu.LAPL: za(900)}
            for trida, platnost in medical.items():
                Medical.objects.create(osoba=osoba, trida=trida, platnost_do=platnost)
            if jen_zak:
                hotovo += 1
                continue  # žák zatím bez licence

            licence = _licence(osoba)
            if Kategorie.MOTOR in kategorie or Kategorie.TMG in kategorie:
                tridy = [D.SEP] if Kategorie.MOTOR in kategorie else []
                if Kategorie.TMG in kategorie:
                    tridy.append(D.TMG)
                if i % 2 == 0:  # PPL(A) s datem platnosti kvalifikací
                    platnost = za(-5) if i % 6 == 4 else za(200 + 40 * i)
                    licence(TypLicence.PPL_A, *[(t, platnost) for t in tridy])
                else:
                    licence(TypLicence.LAPL_A, *[(t, None) for t in tridy])
            if Kategorie.KLUZAK in kategorie:
                zpusoby = [(D.NAVIJAK, None), (D.VLEK, None)]
                if i % 3 == 0:
                    zpusoby.append((D.SAMOSTART, None))
                licence(TypLicence.SPL, *zpusoby)
            if Kategorie.UL in kategorie:
                licence(TypLicence.ULL, (D.ULL, za(-100) if i % 5 == 3 else za(365)))

            if i % 4 != 0:  # každý čtvrtý bez radiofonního průkazu
                licence(TypLicence.RADIO, (D.OFL, za(40) if i % 7 == 2 else za(2500)))
            if i % 3 == 0:
                licence(TypLicence.JAZYK, (D.CS_6, None))
            elif i % 3 == 1:
                licence(TypLicence.JAZYK, (D.EN_4, za(700)), (D.CS_6, None))
            else:
                licence(TypLicence.JAZYK, (D.EN_4, za(-30)))  # prošlá a nic jiného
            hotovo += 1
        self.stdout.write(f"Testovací licence a medical doplněny {hotovo} osobám.")
