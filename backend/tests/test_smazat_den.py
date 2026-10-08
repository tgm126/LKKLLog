"""Admin smaže lety celého dne procedurou v databázi (db/033)."""

import psycopg
import pytest


def _pocet(conn, tabulka: str, lety: list[int]) -> int:
    sloupec = "id" if tabulka == "let" else "let_id"
    return conn.execute(
        f"SELECT count(*) AS n FROM lkkl.{tabulka} WHERE {sloupec} = ANY(%s)",  # noqa: S608
        (lety,),
    ).fetchone()["n"]


def test_smazat_lety_dne(conn, osoba, let):
    pilot, vlekar = osoba("Pilot"), osoba("Vlekar")
    vlecna = let("OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": pilot}, zpusob="VLEK", vlecny_let_id=vlecna)
    motor = let(
        "OK-CRA",
        {"PIC": pilot},
        zpusob="VLASTNI",
        vzlet="now() - interval '2 hours'",
        pristani="now() - interval '1 hour'",
    )
    conn.execute("UPDATE lkkl.let SET pocet_pristani = 2 WHERE id = %s", (motor,))
    conn.execute(
        "INSERT INTO lkkl.let_tg (let_id, cas) VALUES (%s, now() - interval '90 minutes')", (motor,)
    )
    vcera = let(
        "OK-3819",
        {"PIC": pilot},
        vzlet="now() - interval '30 hours'",
        pristani="now() - interval '29 hours'",
    )
    conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    dnes = [vlecna, kluzak, motor]

    # přímo let smazat nejde ani teď
    with pytest.raises(psycopg.errors.RaiseException, match="Let se nemaže"), conn.transaction():
        conn.execute("DELETE FROM lkkl.let WHERE id = %s", (vcera,))

    den = conn.execute("SELECT (now() AT TIME ZONE 'UTC')::date AS d").fetchone()["d"]
    vysledek = conn.execute("CALL lkkl.smazat_lety_dne(%s)", (den,)).fetchone()
    conn.execute("SET CONSTRAINTS ALL IMMEDIATE")  # kontroly letu na konci transakce projdou
    assert vysledek["smazano"] == 3
    assert [_pocet(conn, t, dnes) for t in ("let", "posadka", "let_tg")] == [0, 0, 0]
    assert _pocet(conn, "let", [vcera]) == 1  # jiný den zůstal

    # audit zůstává: smazání s původními hodnotami; příznak mazání po proceduře neplatí
    smazani = conn.execute(
        "SELECT count(*) AS n FROM lkkl.audit WHERE tabulka = 'let' AND operace = 'DELETE'"
    ).fetchone()["n"]
    assert smazani == 3
    with pytest.raises(psycopg.errors.RaiseException, match="Let se nemaže"), conn.transaction():
        conn.execute("DELETE FROM lkkl.let WHERE id = %s", (vcera,))

    prazdny = conn.execute("CALL lkkl.smazat_lety_dne('2000-01-01')").fetchone()
    assert prazdny["smazano"] == 0
