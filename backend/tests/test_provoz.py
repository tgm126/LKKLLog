"""Fáze provozu a zahájení ostrého provozu (db/017_lov_a_faze_provozu.sql)."""

import dataclasses

import psycopg
import pytest

from app import main, prikazy


def _chyba(conn, sql: str) -> str:
    with pytest.raises(psycopg.errors.RaiseException) as e, conn.transaction():
        conn.execute(sql)
    return e.value.diag.message_primary


def test_provozni_tabulky(conn):
    """Každá tabulka bez předpony lov_ (kromě technických) se při zahájení ostrého provozu
    vyprázdní. Nová tabulka změní tento seznam – je třeba vědomě rozhodnout, kam patří
    (trvalá data = předpona lov_)."""
    tabulky = [r["tabulka"] for r in conn.execute("SELECT tabulka FROM lkkl.v_provozni_tabulky")]
    assert tabulky == [
        "audit", "let", "let_tg", "posadka", "relace", "relace_provoz", "relace_provoz_osoba",
    ]  # fmt: skip


def test_zahajeni_ostreho_provozu(conn, osoba, prihlasit):
    novak = osoba("Novak")
    prihlasit("novak@example.cz")
    assert conn.execute("SELECT count(*) AS n FROM lkkl.audit").fetchone()["n"] > 0
    assert conn.execute("SELECT count(*) AS n FROM lkkl.relace").fetchone()["n"] == 1

    vyprazdneno = prikazy.ostry_provoz(conn)
    assert "lkkl.audit" in vyprazdneno and "lkkl.let" in vyprazdneno

    zbyva = conn.execute(
        "SELECT (SELECT count(*) FROM lkkl.audit) + (SELECT count(*) FROM lkkl.relace) AS n"
    ).fetchone()
    assert zbyva["n"] == 0
    # Trvalá data zůstanou (osoba, účet i s heslem).
    ucet = conn.execute("SELECT ma_heslo FROM lkkl.v_ucet WHERE osoba_id = %s", (novak,)).fetchone()
    assert ucet["ma_heslo"]
    assert conn.execute("SELECT faze FROM lkkl.provoz").fetchone()["faze"] == "ostry"

    # Jednou provždy.
    assert _chyba(conn, "SELECT lkkl.zahajit_ostry_provoz()") == "Ostrý provoz už běží."
    assert _chyba(conn, "UPDATE lkkl.provoz SET faze = 'pilot'") == "Ostrý provoz už nejde vrátit."


def test_ostry_provoz_jen_funkci(conn):
    assert _chyba(conn, "UPDATE lkkl.provoz SET faze = 'ostry'").startswith(
        "Ostrý provoz se zahajuje funkcí"
    )
    conn.execute("UPDATE lkkl.provoz SET faze = 'pilot'")  # testování → pilot jde
    assert _chyba(conn, "DELETE FROM lkkl.provoz") == "Fáze provozu se nemaže."


def test_lety_a_audit_nejde_vyprazdnit(conn):
    for tabulka in ("let", "audit"):
        assert _chyba(conn, f"TRUNCATE lkkl.{tabulka} CASCADE").startswith(
            f"Tabulka {tabulka} se nevyprazdňuje"
        )


def test_pruh_podle_faze(klient, conn, monkeypatch):
    produkce = dataclasses.replace(main.nastaveni, prostredi="produkce")
    monkeypatch.setattr(main, "nastaveni", produkce)
    assert klient().get("/api/aplikace").json()["pruh"] == "TESTOVACÍ PROVOZ"
    conn.execute("UPDATE lkkl.provoz SET faze = 'pilot'")
    assert klient().get("/api/aplikace").json()["pruh"] == "PILOTNÍ PROVOZ"
    prikazy.ostry_provoz(conn)
    assert klient().get("/api/aplikace").json()["pruh"] == ""
