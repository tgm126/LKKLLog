"""Připojení k databázi. Spojení jsou v režimu autocommit; co má proběhnout celé, nebo vůbec,
se zabalí do `with conn.transaction():`."""

from collections.abc import Iterator
from contextlib import suppress

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def otevrit(url: str) -> None:
    global _pool
    _pool = ConnectionPool(
        url,
        min_size=1,
        max_size=5,
        kwargs={"autocommit": True, "row_factory": dict_row},
        open=True,
    )


def zavrit() -> None:
    if _pool is not None:
        _pool.close()


def nastavit_kontext(
    conn: Connection, osoba_id: int | None = None, puvodni_osoba_id: int | None = None
) -> None:
    """Řekne databázi, kdo jedná – čte to trigger auditu (db/012_audit.sql).

    Bez osoby jde o akci aplikace bez přihlášení (např. zablokování po neúspěšných pokusech).
    """
    conn.execute(
        """SELECT set_config('lkkl.zdroj', 'aplikace', false),
                  set_config('lkkl.osoba_id', %s, false),
                  set_config('lkkl.puvodni_osoba_id', %s, false)""",
        (str(osoba_id or ""), str(puvodni_osoba_id or "")),
    )


def _zrusit_kontext(conn: Connection) -> None:
    conn.execute(
        """SELECT set_config('lkkl.zdroj', '', false),
                  set_config('lkkl.osoba_id', '', false),
                  set_config('lkkl.puvodni_osoba_id', '', false)"""
    )


def s_kontextem(conn: Connection) -> Iterator[Connection]:
    """Spojení s kontextem auditu na dobu požadavku; po něm se kontext zruší
    (spojení se vrací do poolu a příště může patřit jinému uživateli)."""
    nastavit_kontext(conn)
    try:
        yield conn
    finally:
        with suppress(psycopg.Error):
            _zrusit_kontext(conn)


def spojeni() -> Iterator[Connection]:
    """Závislost FastAPI: spojení z poolu na dobu jednoho požadavku."""
    assert _pool is not None, "Databáze není otevřená."
    with _pool.connection() as conn:
        yield from s_kontextem(conn)
