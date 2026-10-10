"""Nastavení systému (db/034): testovací provoz řídí jen žlutý pruh; lety a audit nejde
vyprázdnit."""

import dataclasses

import psycopg
import pytest

from app import main, nastaveni


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


def test_databaze_z_prostredi(monkeypatch):
    """Připojení: LKKL_DATABAZE má přednost; jinak DB_* z VPS Centra (socket jako cesta
    k souboru → složka a port zvlášť); bez obojího lokální vývojová databáze."""
    for jmeno in ("LKKL_DATABAZE", "DB_NAME", "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_SOCKET"):
        monkeypatch.delenv(jmeno, raising=False)
    assert nastaveni.databaze_z_prostredi() == nastaveni._LOKALNI_DATABAZE

    monkeypatch.setenv("DB_NAME", "lkkllog")
    monkeypatch.setenv("DB_USER", "f84a5")
    monkeypatch.setenv("DB_SOCKET", "/var/run/postgresql/.s.PGSQL.5432")
    casti = set(nastaveni.databaze_z_prostredi().split())
    assert {"dbname=lkkllog", "user=f84a5", "host=/var/run/postgresql", "port=5432"} <= casti
    assert not any(c.startswith("password") for c in casti)

    monkeypatch.setenv("LKKL_DATABAZE", "postgresql://x:y@127.0.0.1/z")
    assert nastaveni.databaze_z_prostredi() == "postgresql://x:y@127.0.0.1/z"


def test_povolene_adresy_z_prostredi(monkeypatch):
    """Víc adres čárkou, mezery a lomítka na konci se odstraní; bez proměnné adresa aplikace."""
    monkeypatch.setenv("LKKL_ADRESA", "https://lety.lkkl.cz/")
    monkeypatch.setenv("LKKL_POVOLENE_ADRESY", "https://lety.lkkl.cz/, https://test.lkkl.cz ,")
    assert nastaveni.nacist().povolene_adresy == {"https://lety.lkkl.cz", "https://test.lkkl.cz"}
    monkeypatch.delenv("LKKL_POVOLENE_ADRESY")
    monkeypatch.setenv("LKKL_PROSTREDI", "produkce")
    monkeypatch.setenv("LKKL_TAJNY_KLIC", "x" * 32)
    assert nastaveni.nacist().povolene_adresy == {"https://lety.lkkl.cz"}
