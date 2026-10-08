"""Nastavení systému (db/034): testovací provoz řídí jen žlutý pruh; lety a audit nejde
vyprázdnit."""

import dataclasses

import psycopg
import pytest

from app import main


def test_pruh_testovaciho_provozu(klient, conn, monkeypatch):
    produkce = dataclasses.replace(main.nastaveni, prostredi="produkce")
    monkeypatch.setattr(main, "nastaveni", produkce)
    assert klient().get("/api/aplikace").json()["pruh"] == "TESTOVACÍ PROVOZ"
    conn.execute("UPDATE lkkl.nastaveni SET testovaci_provoz = false")
    assert klient().get("/api/aplikace").json()["pruh"] == ""
    conn.execute("UPDATE lkkl.nastaveni SET testovaci_provoz = true")  # jde i zpět
    assert klient().get("/api/aplikace").json()["pruh"] == "TESTOVACÍ PROVOZ"


def test_lety_a_audit_nejde_vyprazdnit(conn):
    for tabulka in ("let", "audit"):
        with pytest.raises(psycopg.errors.RaiseException) as e, conn.transaction():
            conn.execute(f"TRUNCATE lkkl.{tabulka} CASCADE")
        assert e.value.diag.message_primary == f"Tabulka {tabulka} se nevyprazdňuje."
