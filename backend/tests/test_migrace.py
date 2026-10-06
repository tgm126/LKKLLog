"""Spouštěč migrací a kontrola stavu."""

import psycopg
import pytest

from app import migrace


@pytest.fixture
def cista_db(databaze):
    """Databáze bez schématu lkkl (po testu se schéma znovu sestaví pro ostatní testy)."""
    with psycopg.connect(databaze, autocommit=True) as c:
        c.execute("DROP SCHEMA lkkl CASCADE")
        yield c
        c.execute("DROP SCHEMA IF EXISTS lkkl CASCADE")
        migrace.provest(c)


def test_provede_vse_a_podruhe_nic(cista_db):
    nove = migrace.provest(cista_db)
    assert nove == [s.name for s in migrace.skripty()] and nove[0].startswith("001_")
    assert migrace.provest(cista_db) == []
    pocet = cista_db.execute("SELECT count(*) FROM lkkl.migrace").fetchone()[0]
    assert pocet == len(nove)


def test_zmeneny_skript_se_odhali(cista_db, tmp_path):
    for skript in migrace.skripty():
        (tmp_path / skript.name).write_text(skript.read_text(encoding="utf-8"), encoding="utf-8")
    migrace.provest(cista_db, tmp_path)
    prvni = sorted(tmp_path.glob("*.sql"))[-1]
    prvni.write_text(prvni.read_text(encoding="utf-8") + "\n-- změna\n", encoding="utf-8")
    with pytest.raises(migrace.ChybaMigrace):
        migrace.provest(cista_db, tmp_path)


def test_jen_oznacit(cista_db, tmp_path):
    (tmp_path / "001_schema.sql").write_text("CREATE SCHEMA lkkl;", encoding="utf-8")
    (tmp_path / "002_tabulka.sql").write_text("CREATE TABLE lkkl.x (id int);", encoding="utf-8")
    migrace.provest(cista_db, tmp_path)  # 001 a 002 provedeno
    (tmp_path / "003_nic.sql").write_text("SELECT nesmysl_ktery_by_spadl();", encoding="utf-8")
    assert migrace.provest(cista_db, tmp_path, jen_oznacit=True) == ["003_nic.sql"]


def test_health(klient):
    odpoved = klient().get("/api/health")
    assert odpoved.status_code == 200 and odpoved.json() == {"stav": "ok", "verze": "vyvoj"}
