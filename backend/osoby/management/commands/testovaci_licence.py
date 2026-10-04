"""Testovací průkazy, medical, radiofonní průkazy a angličtina ICAO.

Jen pro osoby s příznakem „Testovací“ (úklid před spuštěním je smaže i s doklady).
Data jsou pestrá, aby šlo vyzkoušet všechny stavy: v pořádku, brzy vyprší, prošlé,
chybějící. Kategorie se řídí přeškolením osoby na typy letadel, žák = probíhající výcvik.
Osvědčení instruktora a pověření examinátora se nemění. Spuštění:

    uv run python manage.py testovaci_licence            # jen osoby bez dokladů
    uv run python manage.py testovaci_licence --prepsat  # znovu u všech testovacích
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from ciselniky.models import DruhPrukazu, KvalifikacePrukazu, SkupinaPrukazu
from osoby.models import (
    DruhKvalifikace,
    Kategorie,
    KvalifikaceOsoby,
    Osoba,
    PrukazOsoby,
    TridaMedicalu,
    TypLicence,
)

D, M = DruhKvalifikace, TridaMedicalu  # krátké názvy pro přehledné tabulky dat níže

# Doklady, které příkaz vytváří (osvědčení instruktora/examinátora nechává být).
GENEROVANE = [
    SkupinaPrukazu.PILOTNI,
    SkupinaPrukazu.MEDICAL,
    SkupinaPrukazu.RADIO,
    SkupinaPrukazu.JAZYK,
]


def _zakladac(osoba):
    """Funkce, která osobě založí průkaz daného druhu s kvalifikacemi (podle kódů)."""

    def zalozit(kod, *kvalifikace):
        druh = DruhPrukazu.objects.get(kod=kod)
        prukaz = PrukazOsoby.objects.create(
            osoba=osoba, druh=druh, cislo=f"TEST-{osoba.pk}-{kod}", poznamka="testovací"
        )
        for k_kod, platnost in kvalifikace:
            KvalifikaceOsoby.objects.create(
                prukaz=prukaz,
                kvalifikace=KvalifikacePrukazu.objects.get(druh=druh, kod=k_kod),
                platnost_do=platnost,
            )

    return zalozit


class Command(BaseCommand):
    help = "Doplní testovací průkazy a medical osobám s příznakem Testovací."

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
            generovane = PrukazOsoby.objects.filter(osoba=osoba, druh__skupina__in=GENEROVANE)
            if prepsat:
                generovane.delete()
            elif generovane.exists():
                continue  # už má zadané doklady – nepřepisujeme
            kategorie = {p.typ.kategorie for p in osoba.preskoleni.select_related("typ")}
            zak = osoba.vycviky.filter(ukoncen__isnull=True).exists()
            if not kategorie and not zak:
                continue  # nelétá
            zalozit = _zakladac(osoba)

            # Medical: třída 2 a LAPL s různou platností; někdo prošlý, někdo brzy vyprší.
            if i % 5 == 0:
                zalozit("medical", (M.T2, za(-10)), (M.LAPL, za(400)))
            elif i % 5 == 1:
                zalozit("medical", (M.T2, za(20)))
            else:
                zalozit("medical", (M.T2, za(300 + 50 * i)), (M.LAPL, za(900)))
            if zak and not kategorie:  # žák: medical a radiofonní průkaz kvůli sólu
                if i % 4 != 0:
                    zalozit(TypLicence.RADIO, (D.OFL, za(3000)))
                hotovo += 1
                continue

            if Kategorie.MOTOR in kategorie or Kategorie.TMG in kategorie:
                tridy = [D.SEP] if Kategorie.MOTOR in kategorie else []
                if Kategorie.TMG in kategorie:
                    tridy.append(D.TMG)
                vlekani = [(D.VLEKANI, None)] if i % 2 == 0 else []
                if i % 2 == 0:  # PPL(A) s datem platnosti kvalifikací
                    platnost = za(-5) if i % 6 == 4 else za(200 + 40 * i)
                    zalozit(TypLicence.PPL_A, *[(t, platnost) for t in tridy], *vlekani)
                else:
                    zalozit(TypLicence.LAPL_A, *[(t, None) for t in tridy])
            if Kategorie.KLUZAK in kategorie:
                zpusoby = [(D.NAVIJAK, None), (D.VLEK, None)]
                if i % 3 == 0:
                    zpusoby.append((D.SAMOSTART, None))
                zalozit(TypLicence.SPL, *zpusoby)
            if Kategorie.UL in kategorie:
                zalozit(TypLicence.ULL, (D.ULL, za(-100) if i % 5 == 3 else za(365)))

            if i % 4 != 0:  # každý čtvrtý bez radiofonního průkazu
                zalozit(TypLicence.RADIO, (D.OFL, za(40) if i % 7 == 2 else za(2500)))
            if i % 4 == 1:  # angličtinu ICAO má jen pár lidí
                zalozit(TypLicence.JAZYK, (D.EN_4, za(700)) if i % 8 == 1 else (D.EN_6, None))
            hotovo += 1
        self.stdout.write(f"Testovací doklady doplněny {hotovo} osobám.")
