"""Testy běží proti samostatné databázi lkkllog_test (nikdy proti datům uživatele).
Schéma se sestaví ze skriptů db/NNN_*.sql (bez _data); každý test běží v transakci,
která se na konci vrátí."""

import os
from pathlib import Path

ZAKLAD = "postgresql://lkkllog:lkkllog@127.0.0.1:5432"
TESTOVACI_DB = "lkkllog_test"
ADRESA = "https://testserver"

os.environ["LKKL_DATABAZE"] = f"{ZAKLAD}/{TESTOVACI_DB}"
os.environ["LKKL_ADRESA"] = "https://lety.test"
os.environ["LKKL_POVOLENE_ADRESY"] = ADRESA

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from psycopg.rows import dict_row  # noqa: E402

from app import bezpecnost  # noqa: E402
from app.db import s_kontextem, spojeni  # noqa: E402
from app.main import app  # noqa: E402

SKRIPTY = Path(__file__).resolve().parents[2] / "db"
HESLO = "spravne-heslo-123"


@pytest.fixture(scope="session")
def databaze() -> str:
    with psycopg.connect(f"{ZAKLAD}/lkkllog", autocommit=True) as c:
        if not c.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (TESTOVACI_DB,)
        ).fetchone():
            c.execute(f"CREATE DATABASE {TESTOVACI_DB}")
    url = f"{ZAKLAD}/{TESTOVACI_DB}"
    with psycopg.connect(url, autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS lkkl CASCADE")
        for skript in sorted(SKRIPTY.glob("[0-9][0-9][0-9]_*.sql")):
            if not skript.stem.endswith("_data"):
                c.execute(skript.read_text(encoding="utf-8"))
    return url


@pytest.fixture
def conn(databaze):
    with (
        psycopg.connect(databaze, autocommit=True, row_factory=dict_row) as c,
        c.transaction(force_rollback=True),
    ):
        yield c


@pytest.fixture
def klient(conn):
    """Továrna na klienty (každý má vlastní cookie = vlastní zařízení)."""

    def _spojeni():
        yield from s_kontextem(conn)

    app.dependency_overrides[spojeni] = _spojeni

    def novy(origin: str | None = ADRESA) -> TestClient:
        return TestClient(app, base_url=ADRESA, headers={"Origin": origin} if origin else {})

    yield novy
    app.dependency_overrides.clear()


@pytest.fixture
def osoba(conn):
    """Založí osobu, případně s účtem a heslem; vrátí id."""

    def zalozit(
        prijmeni: str = "Pilot",
        email: str | None = None,
        ucet: bool = True,
        heslo: str | None = HESLO,
        **prava,
    ) -> int:
        email = email or f"{prijmeni.lower()}@example.cz"
        osoba_id = conn.execute(
            "INSERT INTO lkkl.osoba (jmeno, prijmeni, email) VALUES ('Jan', %s, %s) RETURNING id",
            (prijmeni, email),
        ).fetchone()["id"]
        if ucet:
            conn.execute(
                """INSERT INTO lkkl.ucet (osoba_id, heslo_hash, admin, smi_odblokovat)
                   VALUES (%s, %s, %s, %s)""",
                (
                    osoba_id,
                    bezpecnost.otisk_hesla(heslo) if heslo else None,
                    prava.get("admin", False),
                    prava.get("smi_odblokovat", False),
                ),
            )
        return osoba_id

    return zalozit


@pytest.fixture
def prihlasit(klient):
    """Nový klient přihlášený daným e-mailem."""

    def prihlasit(email: str, heslo: str = HESLO) -> TestClient:
        k = klient()
        odpoved = k.post("/api/prihlaseni", json={"email": email, "heslo": heslo})
        assert odpoved.status_code == 200, odpoved.text
        return k

    return prihlasit
