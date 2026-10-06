"""Příkazy pro správu z příkazové řádky.

uv run python -m app.prikazy odkaz <e-mail>   odkaz pro nastavení hesla (např. první admin)
uv run python -m app.prikazy uklid            smaže prošlé relace
uv run python -m app.prikazy ostry-provoz --potvrzuji
    zahájí ostrý provoz: NEVRATNĚ vyprázdní provozní tabulky (lety, audit, relace…);
    předtím úplná záloha databáze
"""

import sys

import psycopg
from psycopg.rows import dict_row

from .nastaveni import nastaveni
from .prihlasovani import odkaz_pro_heslo


def odkaz(conn: psycopg.Connection, email: str) -> str:
    u = conn.execute(
        """SELECT u.osoba_id, u.heslo_zmeneno, v.smi_se_prihlasit
           FROM lkkl.ucet u JOIN lkkl.v_ucet v ON v.osoba_id = u.osoba_id
           WHERE lower(v.email) = lower(%s)""",
        (email.strip(),),
    ).fetchone()
    if u is None:
        raise SystemExit(f"Účet s e-mailem {email} neexistuje.")
    if not u["smi_se_prihlasit"]:
        raise SystemExit("Účet nebo osoba je zablokovaná.")
    return odkaz_pro_heslo(u["osoba_id"], u["heslo_zmeneno"])


def uklid(conn: psycopg.Connection) -> int:
    return conn.execute("DELETE FROM lkkl.relace WHERE plati_do <= now()").rowcount


def ostry_provoz(conn: psycopg.Connection) -> str:
    """Vyprázdní provozní tabulky a nastaví fázi ostry (lkkl.zahajit_ostry_provoz)."""
    with conn.transaction():
        return conn.execute("SELECT lkkl.zahajit_ostry_provoz() AS t").fetchone()["t"]


def main(argv: list[str]) -> None:
    with psycopg.connect(nastaveni.databaze, autocommit=True, row_factory=dict_row) as conn:
        match argv:
            case ["odkaz", email]:
                print(odkaz(conn, email))
            case ["uklid"]:
                print(f"Smazáno prošlých relací: {uklid(conn)}")
            case ["ostry-provoz", "--potvrzuji"]:
                print(f"Ostrý provoz zahájen, vyprázdněno: {ostry_provoz(conn)}")
            case _:
                raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
