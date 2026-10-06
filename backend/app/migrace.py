"""Spouštěč migrací: provede nové SQL skripty `db/NNN_*.sql` (bez `_data`) v pořadí čísel.

Provedené skripty eviduje tabulka `lkkl.migrace` (skript, kdy, otisk obsahu). Každý skript
běží ve vlastní transakci; při chybě se skončí (na serveru se pak nespustí aplikace). Změna už
provedeného skriptu se pozná podle otisku a je to chyba – opravy patří do nového skriptu.

    uv run python -m app.migrace                       provede nové skripty
    uv run python -m app.migrace --oznacit-provedene   jen zapíše skripty jako provedené
                                                       (databáze, kde se spouštěly ručně)
"""

import hashlib
import sys
from pathlib import Path

import psycopg

from .nastaveni import nastaveni

ADRESAR = Path(__file__).resolve().parents[2] / "db"

_TABULKA = """CREATE TABLE IF NOT EXISTS lkkl.migrace (
    skript text        PRIMARY KEY,
    kdy    timestamptz NOT NULL DEFAULT now(),
    otisk  text        NOT NULL
)"""


class ChybaMigrace(RuntimeError):
    pass


def skripty(adresar: Path = ADRESAR) -> list[Path]:
    return sorted(s for s in adresar.glob("[0-9][0-9][0-9]_*.sql") if not s.stem.endswith("_data"))


def _otisk(skript: Path) -> str:
    return hashlib.sha256(skript.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _schema_existuje(conn: psycopg.Connection) -> bool:
    return conn.execute("SELECT 1 FROM pg_namespace WHERE nspname = 'lkkl'").fetchone() is not None


def _provedene(conn: psycopg.Connection) -> dict[str, str]:
    if not _schema_existuje(conn):
        return {}
    conn.execute(_TABULKA)
    return dict(conn.execute("SELECT skript, otisk FROM lkkl.migrace").fetchall())


def provest(
    conn: psycopg.Connection, adresar: Path = ADRESAR, jen_oznacit: bool = False
) -> list[str]:
    """Provede (nebo jen označí) nové skripty; vrátí jejich jména. Spojení musí mít autocommit."""
    provedene = _provedene(conn)
    nove = []
    for skript in skripty(adresar):
        otisk = _otisk(skript)
        if skript.name in provedene:
            if provedene[skript.name] != otisk:
                raise ChybaMigrace(
                    f"Skript {skript.name} se po provedení změnil – opravu dejte do nového skriptu."
                )
            continue
        with conn.transaction():
            if not jen_oznacit:
                conn.execute(skript.read_text(encoding="utf-8"))
            conn.execute(_TABULKA)  # první skript teprve zakládá schéma lkkl
            conn.execute(
                "INSERT INTO lkkl.migrace (skript, otisk) VALUES (%s, %s)", (skript.name, otisk)
            )
        nove.append(skript.name)
    return nove


def main(argv: list[str]) -> None:
    jen_oznacit = argv == ["--oznacit-provedene"]
    if argv and not jen_oznacit:
        raise SystemExit(__doc__)
    with psycopg.connect(nastaveni.databaze, autocommit=True) as conn:
        try:
            nove = provest(conn, jen_oznacit=jen_oznacit)
        except (ChybaMigrace, psycopg.Error) as e:
            raise SystemExit(f"Migrace selhala: {e}") from e
    akce = "Označeno jako provedené" if jen_oznacit else "Provedeno"
    print(f"{akce}: {', '.join(nove)}" if nove else "Databáze je aktuální.")


if __name__ == "__main__":
    main(sys.argv[1:])
