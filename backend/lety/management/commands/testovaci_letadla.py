"""Testovací stav provozních deníků a termíny letadel (pro zkoušení přehledu letadel).

Termíny mají poznámku „testovací“, aby je šlo před spuštěním ostrého provozu poznat
a smazat; stav deníku se při spuštění zadává znovu podle skutečných deníků.
Bere jen aktivní klubová letadla (soukromá ne). Data jsou pestrá: v pořádku, brzy,
prošlé – podle data i podle náletu. Spuštění:

    uv run python manage.py testovaci_letadla            # jen letadla bez deníku a termínů
    uv run python manage.py testovaci_letadla --prepsat  # znovu u všech
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from lety.letadla import nalet_min, s_naletem
from lety.models import Letadlo, TerminLetadla
from osoby.models import Kategorie

POZNAMKA = "testovací"


class Command(BaseCommand):
    help = "Doplní testovací stav deníků a termíny klubovým letadlům."

    def add_arguments(self, parser):
        parser.add_argument("--prepsat", action="store_true", help="Smazat a vytvořit znovu.")

    @transaction.atomic
    def handle(self, *args, prepsat=False, **options):
        dnes = timezone.now().date()
        za = lambda dni: dnes + timedelta(days=dni)  # noqa: E731
        letadla = Letadlo.objects.filter(aktivni=True, soukrome=False).order_by("poradi", "pk")
        hotovo = 0
        for i, letadlo in enumerate(letadla):
            if prepsat:
                letadlo.terminy.filter(poznamka=POZNAMKA).delete()
            elif letadlo.stav_k or letadlo.terminy.exists():
                continue  # už má zadané údaje – nepřepisujeme

            # Stav deníku před měsícem; lety z evidence po něm se přičtou.
            kluzak = letadlo.kategorie == Kategorie.KLUZAK
            letadlo.nalet_pocatek_min = (800 + 137 * i) * 60 + 7 * i % 60
            letadlo.starty_pocatek = (4000 if kluzak else 1500) + 311 * i
            letadlo.stav_k = za(-30)
            letadlo.save(update_fields=["nalet_pocatek_min", "starty_pocatek", "stav_k"])
            hodiny = nalet_min(s_naletem().get(pk=letadlo.pk)) // 60

            def termin(nazev, datum=None, pri_naletu_h=None, letadlo=letadlo):
                TerminLetadla.objects.create(
                    letadlo=letadlo,
                    nazev=nazev,
                    datum=datum,
                    pri_naletu_h=pri_naletu_h,
                    poznamka=POZNAMKA,
                )

            # ARC: prošlé / brzy / v pořádku; pojištění vždy v pořádku.
            termin("ARC", datum=[za(-3), za(20), za(200), za(300)][i % 4])
            termin("Pojištění", datum=za(100 + 40 * i))
            if kluzak:
                termin("Roční prohlídka", datum=za(60 + 30 * i))
            else:
                # 100h prohlídka: brzy (zbývá 5 h) / překročená / v pořádku (60 h).
                termin("100h prohlídka", pri_naletu_h=hodiny + [5, -1, 60][i % 3])
                termin("Generální oprava motoru (TBO)", pri_naletu_h=hodiny + 400 + 50 * i)
            if letadlo.kategorie == Kategorie.UL:
                termin("Technický průkaz", datum=za(-10) if i % 2 else za(400))
                termin("Záchranný systém", datum=za(500))
            hotovo += 1
        self.stdout.write(f"Testovací stav deníku a termíny doplněny {hotovo} letadlům.")
