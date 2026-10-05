"""Připojení k databázi. Spojení jsou v režimu autocommit; co má proběhnout celé, nebo vůbec,
se zabalí do `with conn.transaction():`."""

from collections.abc import Iterator

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


def spojeni() -> Iterator[Connection]:
    """Závislost FastAPI: spojení z poolu na dobu jednoho požadavku."""
    assert _pool is not None, "Databáze není otevřená."
    with _pool.connection() as conn:
        yield conn
