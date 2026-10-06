"""Nastavení z proměnných prostředí (LKKL_*; databázi na serveru dává VPS Centrum v DB_*)."""

import os
from dataclasses import dataclass
from pathlib import Path

from psycopg.conninfo import make_conninfo

# Jen pro lokální vývoj; v produkci musí být LKKL_TAJNY_KLIC nastavený.
_VYVOJOVY_KLIC = "vyvoj-tento-klic-neni-tajny-0123456789"  # noqa: S105
_LOKALNI_DATABAZE = "postgresql://lkkllog:lkkllog@127.0.0.1:5432/lkkllog"
# Soubor VERZE zapisuje CI při nasazení (číslo značky); lokálně neexistuje.
_SOUBOR_VERZE = Path(__file__).resolve().parents[1] / "VERZE"
# Sestavený frontend (npm run build); v Dockeru /srv/lkkl/frontend/dist.
_FRONTEND = Path(__file__).resolve().parents[2] / "frontend" / "dist"


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
    verze: str
    frontend: Path
    """Složka se sestaveným frontendem; když neexistuje, server vrací jen rozhraní /api."""

    @property
    def vyvoj(self) -> bool:
        return self.prostredi == "vyvoj"


def databaze_z_prostredi() -> str:
    """LKKL_DATABAZE, jinak databáze přiřazená ve VPS Centru (DB_*), jinak lokální vývojová.

    Na serveru jde připojení unixovým socketem bez hesla (PostgreSQL ověří uživatele podle
    systémového účtu kontejneru); DB_SOCKET může být cesta k souboru socketu – psycopg chce
    složku a port zvlášť.
    """
    if url := os.environ.get("LKKL_DATABAZE"):
        return url
    if not os.environ.get("DB_NAME"):
        return _LOKALNI_DATABAZE
    host = os.environ.get("DB_SOCKET") or os.environ.get("DB_HOST", "")
    port = ""
    if "/.s.PGSQL." in host:
        host, port = host.rsplit("/.s.PGSQL.", 1)
    casti = {
        "dbname": os.environ["DB_NAME"],
        "user": os.environ.get("DB_USER"),
        "password": os.environ.get("DB_PASSWORD"),
        "host": host or None,
        "port": port or None,
        "connect_timeout": 5,
    }
    return make_conninfo(**{k: v for k, v in casti.items() if v})


def nacist() -> Nastaveni:
    prostredi = os.environ.get("LKKL_PROSTREDI", "vyvoj")
    tajny_klic = os.environ.get("LKKL_TAJNY_KLIC", "")
    if not tajny_klic:
        if prostredi != "vyvoj":
            raise RuntimeError("Chybí proměnná prostředí LKKL_TAJNY_KLIC.")
        tajny_klic = _VYVOJOVY_KLIC
    adresa = os.environ.get("LKKL_ADRESA", "http://localhost:5173").rstrip("/")
    vychozi = adresa if prostredi != "vyvoj" else f"{adresa},http://localhost:8000"
    povolene = os.environ.get("LKKL_POVOLENE_ADRESY", vychozi)
    verze = _SOUBOR_VERZE.read_text(encoding="utf-8").strip() if _SOUBOR_VERZE.exists() else "vyvoj"
    return Nastaveni(
        prostredi=prostredi,
        databaze=databaze_z_prostredi(),
        tajny_klic=tajny_klic,
        adresa=adresa,
        povolene_adresy=frozenset(a.strip().rstrip("/") for a in povolene.split(",") if a.strip()),
        verze=verze,
        frontend=Path(os.environ.get("LKKL_FRONTEND", _FRONTEND)),
    )


nastaveni = nacist()
