"""Nastavení z proměnných prostředí (předpona LKKL_)."""

import os
from dataclasses import dataclass

# Jen pro lokální vývoj; v produkci musí být LKKL_TAJNY_KLIC nastavený.
_VYVOJOVY_KLIC = "vyvoj-tento-klic-neni-tajny-0123456789"  # noqa: S105


@dataclass(frozen=True)
class Nastaveni:
    prostredi: str
    """vyvoj | produkce"""
    databaze: str
    tajny_klic: str
    """Podpis odkazů pro nastavení hesla."""
    adresa: str
    """Adresa aplikace v prohlížeči (pro odkazy)."""
    povolene_adresy: frozenset[str]
    """Hodnoty hlavičky Origin, ze kterých smí přijít požadavek, který něco mění."""

    @property
    def vyvoj(self) -> bool:
        return self.prostredi == "vyvoj"


def nacist() -> Nastaveni:
    prostredi = os.environ.get("LKKL_PROSTREDI", "vyvoj")
    tajny_klic = os.environ.get("LKKL_TAJNY_KLIC", "")
    if not tajny_klic:
        if prostredi != "vyvoj":
            raise RuntimeError("Chybí proměnná prostředí LKKL_TAJNY_KLIC.")
        tajny_klic = _VYVOJOVY_KLIC
    adresa = os.environ.get("LKKL_ADRESA", "http://localhost:5173").rstrip("/")
    povolene = os.environ.get("LKKL_POVOLENE_ADRESY", f"{adresa},http://localhost:8000")
    return Nastaveni(
        prostredi=prostredi,
        databaze=os.environ.get(
            "LKKL_DATABAZE", "postgresql://lkkllog:lkkllog@127.0.0.1:5432/lkkllog"
        ),
        tajny_klic=tajny_klic,
        adresa=adresa,
        povolene_adresy=frozenset(a.strip().rstrip("/") for a in povolene.split(",") if a.strip()),
    )


nastaveni = nacist()
