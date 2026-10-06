"""Databáze pro klikací testy (Playwright): lkkllog_e2e sestavená ze skriptů db/ a dvě osoby.

Spouští ji frontend/playwright.config.ts před startem serveru:
    uv run python -m tests.e2e_priprava
Data uživatele (databáze lkkllog) nikdy nepoužívá.
"""

import os

import psycopg

from app import bezpecnost, migrace

ZAKLAD = os.environ.get("LKKL_E2E_ZAKLAD", "postgresql://lkkllog:lkkllog@127.0.0.1:5432")
DATABAZE = "lkkllog_e2e"
HESLO_ADMINA = "heslo-pro-e2e-test"  # noqa: S105 – jen testovací databáze


def pripravit() -> None:
    with psycopg.connect(f"{ZAKLAD}/lkkllog", autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABAZE,)).fetchone():
            c.execute(f"CREATE DATABASE {DATABAZE}")
    with psycopg.connect(f"{ZAKLAD}/{DATABAZE}", autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS lkkl CASCADE")
        migrace.provest(c)
        with c.transaction():
            admin = c.execute(
                """INSERT INTO lkkl.lov_osoba (jmeno, prijmeni, email)
                   VALUES ('Adam', 'Admin', 'admin@example.cz') RETURNING id"""
            ).fetchone()[0]
            c.execute(
                "INSERT INTO lkkl.ucet (osoba_id, heslo_hash, admin) VALUES (%s, %s, true)",
                (admin, bezpecnost.otisk_hesla(HESLO_ADMINA)),
            )
            nova = c.execute(
                """INSERT INTO lkkl.lov_osoba (jmeno, prijmeni, email)
                   VALUES ('Nela', 'Nová', 'nova@example.cz') RETURNING id"""
            ).fetchone()[0]
            c.execute("INSERT INTO lkkl.ucet (osoba_id) VALUES (%s)", (nova,))


if __name__ == "__main__":
    pripravit()
