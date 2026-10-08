"""Příkazy pro správu z příkazové řádky.

uv run python -m app.prikazy odkaz <e-mail>   odkaz pro nastavení hesla (např. první admin)
uv run python -m app.prikazy uklid            smaže prošlé relace
"""

import sys

import psycopg
from psycopg.rows import dict_row

from .nastaveni import nastaveni
from .prihlasovani import odkaz_pro_heslo, smazat_relace


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
    return smazat_relace(conn, "plati_do <= now()", ())


def main(argv: list[str]) -> None:
    with psycopg.connect(nastaveni.databaze, autocommit=True, row_factory=dict_row) as conn:
        match argv:
            case ["odkaz", email]:
                print(odkaz(conn, email))
            case ["uklid"]:
                print(f"Smazáno prošlých relací: {uklid(conn)}")
            case _:
                raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
