"""Připojení k databázi. Spojení jsou v režimu autocommit; co má proběhnout celé, nebo vůbec,
se zabalí do `with transakce(conn, …):` – chyby databáze se přitom přeloží na srozumitelné
odpovědi (pravidla žijí v databázi, server je jen tlumočí; code review 9. 10. 2026, S3)."""

import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress

import psycopg
from fastapi import HTTPException
from psycopg import Connection, errors
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def otevrit(url: str) -> None:
    global _pool
    _pool = ConnectionPool(
        url,
        min_size=1,
        max_size=10,
        # Bez připravených dotazů (prepared statements): jejich plán by po ruční změně pohledu
        # nebo tabulky v databázi (a po obnově testovací databáze) skončil chybou „cached plan
        # must not change result type“. Dotazy jsou malé, rozdíl ve výkonu není znát.
        kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": None},
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


def pripojeni():
    """Spojení z poolu mimo požadavek (start aplikace): `with db.pripojeni() as conn:`."""
    if _pool is None:
        raise RuntimeError("Databáze není otevřená.")
    return _pool.connection()


def spojeni() -> Iterator[Connection]:
    """Závislost FastAPI: spojení z poolu na dobu jednoho požadavku."""
    with pripojeni() as conn:
        yield from s_kontextem(conn)


# --- chyby databáze jako odpovědi ------------------------------------------------------------

Hlasky = Mapping[str | type[errors.Error], str]
"""Hlášky k chybám databáze: podle názvu omezení (přesně), nebo podle druhu chyby (modul)."""

# Druh chyby → stav HTTP a hláška, když modul nedá vlastní. Cizí klíč má dvě podoby: chybějící
# cíl při vložení (404) a smazání něčeho, na co se odkazuje (409).
_VYCHOZI: dict[type[errors.Error], tuple[int, str]] = {
    errors.RaiseException: (400, ""),  # text dává databáze (RAISE EXCEPTION v triggeru)
    errors.CheckViolation: (400, "Údaje nejdou uložit."),
    errors.UniqueViolation: (400, "Už existuje."),
    errors.ExclusionViolation: (409, "Překrývá se s jiným záznamem."),
    errors.ForeignKeyViolation: (409, "Je použito – nejde smazat, jen zneplatnit."),
}
_FK_CHYBI_CIL = (404, "Odkazovaný záznam neexistuje.")


def chyba_db(
    e: errors.Error, hlasky: Hlasky | None = None, predpona: str | None = None
) -> HTTPException | None:
    """Chyba databáze jako HTTP odpověď, nebo None, když to není chyba pravidel (ta zůstane
    chybou serveru). Hláška: podle názvu omezení, pak podle druhu chyby z `hlasky`, pak
    výchozí; u RAISE text databáze (bez `predpony`, např. „Let 12: “)."""
    hlasky = hlasky or {}
    druh = next((d for d in _VYCHOZI if isinstance(e, d)), None)
    if druh is None:
        return None
    stav, text = _VYCHOZI[druh]
    if druh is errors.ForeignKeyViolation and (e.diag.message_primary or "").startswith("insert"):
        stav, text = _FK_CHYBI_CIL
    if druh is errors.RaiseException:
        text = e.diag.message_primary or text
        if predpona:
            text = re.sub(predpona, "", text, count=1)
            text = text[:1].upper() + text[1:]
    text = hlasky.get(e.diag.constraint_name or "", hlasky.get(druh, text))
    return HTTPException(stav, text)


@contextmanager
def transakce(
    conn: Connection,
    hlasky: Hlasky | None = None,
    odlozene: bool = False,
    predpona: str | None = None,
) -> Iterator[None]:
    """Změna v jedné transakci; chyby pravidel databáze se vrátí jako srozumitelná odpověď.
    `odlozene`: kontroly odložené na konec transakce (CONSTRAINT TRIGGER … DEFERRABLE) se
    vyhodnotí až po všech příkazech, i když je předchozí změna přepnula na okamžité."""
    try:
        with conn.transaction():
            if odlozene:
                conn.execute("SET CONSTRAINTS ALL DEFERRED")
            yield
            if odlozene:
                conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    except errors.Error as e:
        odpoved = chyba_db(e, hlasky, predpona)
        if odpoved is None:
            raise
        raise odpoved from e


def upravit(
    conn: Connection,
    tabulka: str,
    id_: int,
    zmeny: Mapping[str, object],
    beze_zmeny: str | None = None,
) -> bool:
    """UPDATE jen zadaných sloupců podle id; vrátí, zda řádek existuje. Názvy sloupců smějí
    pocházet jen z pevných modelů (Pydantic), nikdy od uživatele. Bez změn se řádek jen ověří,
    nebo – s `beze_zmeny` (např. "verze = verze") – „dotkne“, aby se spustil trigger."""
    nastavit = ", ".join(f"{s} = %({s})s" for s in zmeny) or beze_zmeny
    if nastavit is None:
        return (
            conn.execute(
                f"SELECT 1 FROM lkkl.{tabulka} WHERE id = %s",  # noqa: S608 – pevný název
                (id_,),
            ).fetchone()
            is not None
        )
    radek = conn.execute(
        f"UPDATE lkkl.{tabulka} SET {nastavit} WHERE id = %(id)s RETURNING id",  # noqa: S608
        {**zmeny, "id": id_},
    ).fetchone()
    return radek is not None
