"""Číselníky: seznamy možných hodnot, na které se odkazují karty osob a letadel.

Hodnoty se systémovým kódem (`kod`) zná aplikace a počítá s nimi pravidla (např. SEP,
vlekání, FI(S), medical LAPL) – lze je přejmenovat a deaktivovat, ne smazat. Hodnoty
přidané adminem se jen evidují.
"""

from django.contrib.postgres.fields import ArrayField
from django.db import models

from osoby.models import Kategorie


class Polozka(models.Model):
    """Společné vlastnosti položky číselníku."""

    nazev = models.CharField("název", max_length=80)
    # NULL místo "" – jedinečnost kódu nesmí vadit u položek bez kódu.
    kod = models.CharField(  # noqa: DJ001
        "systémový kód",
        max_length=30,
        null=True,
        blank=True,
        help_text="Hodnota, se kterou počítají pravidla aplikace. Nemazat.",
    )
    aktivni = models.BooleanField("aktivní", default=True)
    poradi = models.PositiveSmallIntegerField("pořadí", default=100)

    class Meta:
        abstract = True
        ordering = ["poradi", "nazev"]

    def __str__(self):
        return self.nazev

    @property
    def systemova(self) -> bool:
        return bool(self.kod)


def _kategorie():
    return ArrayField(
        models.CharField(max_length=10, choices=Kategorie.choices),
        default=list,
        blank=True,
        verbose_name="kategorie letadel",
    )


class TypLetadla(Polozka):
    kategorie = models.CharField(max_length=10, choices=Kategorie.choices)

    class Meta(Polozka.Meta):
        verbose_name = "typ letadla"
        verbose_name_plural = "typy letadel"
        constraints = [models.UniqueConstraint(fields=["nazev"], name="typ_letadla_unikatni")]


class SkupinaPrukazu(models.TextChoices):
    PILOTNI = "pilotni", "Pilotní průkaz"
    INSTRUKTOR = "instruktor", "Instruktor"
    EXAMINATOR = "examinator", "Examinátor"
    MEDICAL = "medical", "Medical"
    RADIO = "radio", "Radiofonní průkaz"
    JAZYK = "jazyk", "Jazyk"


class DruhPrukazu(Polozka):
    """Průkaz nebo doklad, který osoba může mít (PPL(A), SPL, medical, radiofonní…)."""

    skupina = models.CharField(max_length=12, choices=SkupinaPrukazu.choices)
    kategorie = _kategorie()

    class Meta(Polozka.Meta):
        verbose_name = "druh průkazu"
        verbose_name_plural = "druhy průkazů"
        ordering = ["poradi", "nazev"]
        constraints = [
            models.UniqueConstraint(fields=["nazev"], name="druh_prukazu_unikatni"),
            models.UniqueConstraint(fields=["kod"], name="druh_prukazu_kod"),
        ]


class KvalifikacePrukazu(Polozka):
    """Kvalifikace, třída nebo úroveň v rámci druhu průkazu (SEP, naviják, třída 2…)."""

    druh = models.ForeignKey(DruhPrukazu, on_delete=models.PROTECT, related_name="kvalifikace")
    ma_platnost = models.BooleanField(
        "má datum platnosti", default=False, help_text="Na kartě se u ní zadává datum."
    )
    kategorie = _kategorie()

    class Meta(Polozka.Meta):
        verbose_name = "kvalifikace průkazu"
        verbose_name_plural = "kvalifikace průkazů"
        constraints = [
            models.UniqueConstraint(fields=["druh", "nazev"], name="kvalifikace_unikatni"),
            models.UniqueConstraint(fields=["druh", "kod"], name="kvalifikace_kod"),
        ]


class ProvozniOpravneni(Polozka):
    """Činnost v provozu, ke které je člověk způsobilý (navijákář, služba RADIO…)."""

    class Meta(Polozka.Meta):
        verbose_name = "provozní oprávnění"
        verbose_name_plural = "provozní oprávnění"
        constraints = [models.UniqueConstraint(fields=["nazev"], name="provozni_unikatni")]


class DruhTerminu(Polozka):
    """Druh termínu u letadla (ARC, roční prohlídka, pojištění…)."""

    class Meta(Polozka.Meta):
        verbose_name = "druh termínu letadla"
        verbose_name_plural = "druhy termínů letadel"
        constraints = [models.UniqueConstraint(fields=["nazev"], name="druh_terminu_unikatni")]
