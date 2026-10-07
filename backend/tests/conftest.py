"""Testy běží proti samostatné databázi lkkllog_test (nikdy proti datům uživatele).
Schéma sestaví spouštěč migrací ze skriptů db/NNN_*.sql (bez _data); každý test běží
v transakci, která se na konci vrátí."""

import os

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

from app import bezpecnost, migrace  # noqa: E402
from app.db import s_kontextem, spojeni  # noqa: E402
from app.main import app  # noqa: E402

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
        migrace.provest(c)
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
            """INSERT INTO lkkl.lov_osoba (jmeno, prijmeni, email)
               VALUES ('Jan', %s, %s) RETURNING id""",
            (prijmeni, email),
        ).fetchone()["id"]
        if ucet:
            conn.execute(
                """INSERT INTO lkkl.ucet
                       (osoba_id, heslo_hash, admin, smi_odblokovat, spravuje_osoby,
                        spravuje_letadla)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (
                    osoba_id,
                    bezpecnost.otisk_hesla(heslo) if heslo else None,
                    prava.get("admin", False),
                    prava.get("smi_odblokovat", False),
                    prava.get("spravuje_osoby", False),
                    prava.get("spravuje_letadla", False),
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


@pytest.fixture
def pilot(osoba, prihlasit):
    """Přihlášený pilot (id, klient)."""
    pilot_id = osoba("Pilot")
    return pilot_id, prihlasit("pilot@example.cz")


# --- lety -------------------------------------------------------------------------------------


def _id(conn, tabulka: str, kod: str) -> int:
    return conn.execute(f"SELECT id FROM lkkl.{tabulka} WHERE kod = %s", (kod,)).fetchone()["id"]  # noqa: S608


@pytest.fixture
def flotila(conn):
    """Kategorie, typy, letadla a letiště (v testovací databázi nejsou data uživatele)."""
    conn.execute(
        """INSERT INTO lkkl.lov_kategorie (kod, nazev, poradi)
           VALUES ('KLUZAK', 'Kluzák', 10), ('LETOUN', 'Letoun', 30)"""
    )
    conn.execute(
        """INSERT INTO lkkl.lov_typ (kod, nazev, poradi, kategorie_id, pocet_mist)
           SELECT v.kod, v.nazev, v.poradi, k.id, v.mist
           FROM (VALUES ('L13', 'L 13', 10, 'KLUZAK', 2), ('Z526', 'Z 526', 20, 'LETOUN', 2))
                AS v(kod, nazev, poradi, kat, mist)
           JOIN lkkl.lov_kategorie k ON k.kod = v.kat"""
    )
    conn.execute(
        """INSERT INTO lkkl.lov_letadlo (rejstrik, typ_id, vlecne, max_doba_min)
           VALUES ('OK-2817', (SELECT id FROM lkkl.lov_typ WHERE kod = 'L13'), false, NULL),
                  ('OK-3819', (SELECT id FROM lkkl.lov_typ WHERE kod = 'L13'), false, 60),
                  ('OK-CRA', (SELECT id FROM lkkl.lov_typ WHERE kod = 'Z526'), true, NULL)"""
    )
    conn.execute(
        """INSERT INTO lkkl.lov_letiste (kod, nazev, domovske, zem_sirka, zem_delka, poradi)
           VALUES ('LKKL', 'Kladno', true, 50.1128, 14.0897, 10),
                  ('LKLT', 'Letňany', false, 50.1314, 14.5257, 20)"""
    )


@pytest.fixture
def let(conn, osoba, flotila):
    """Založí let; časy jako SQL výraz vůči now() (v transakci testu je now() stálý)."""
    zalozil = osoba("Casomeric")

    def zalozit(
        rejstrik: str,
        posadka: dict[str, int],
        ucel: str | None = "NORMALNI",
        zpusob: str = "NAVIJAK",
        vzlet: str | None = None,
        pristani: str | None = None,
        pob: int | None = 1,
        misto_pristani: str = "LKKL",
        vlecny_let_id: int | None = None,
        zrusit: bool = False,
    ) -> int:
        let_id = conn.execute(
            f"""INSERT INTO lkkl.let (letadlo_id, ucel_id, zpusob_vzletu_id, vlecny_let_id,
                    cas_vzletu, cas_pristani, misto_pristani_id, pocet_pristani, pob,
                    plati_aeroklub, zalozil_id)
                VALUES ((SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = %(rejstrik)s),
                        (SELECT id FROM lkkl.lov_ucel WHERE kod = %(ucel)s),
                        (SELECT id FROM lkkl.lov_zpusob_vzletu WHERE kod = %(zpusob)s),
                        %(vlecny)s, {vzlet or "NULL"}, {pristani or "NULL"},
                        (SELECT id FROM lkkl.lov_letiste WHERE kod = %(misto)s),
                        CASE WHEN {pristani or "NULL"} IS NOT NULL THEN 1 END,
                        %(pob)s, true, %(zalozil)s)
                RETURNING id""",  # noqa: S608 – jen pevné výrazy z testu
            {
                "rejstrik": rejstrik,
                "ucel": ucel,
                "zpusob": zpusob,
                "vlecny": vlecny_let_id,
                "misto": misto_pristani,
                "pob": pob,
                "zalozil": zalozil,
            },
        ).fetchone()["id"]
        for funkce, osoba_id in posadka.items():
            conn.execute(
                "INSERT INTO lkkl.posadka (let_id, osoba_id, funkce_id) VALUES (%s, %s, %s)",
                (let_id, osoba_id, _id(conn, "lov_funkce", funkce)),
            )
        if zrusit:
            conn.execute(
                """UPDATE lkkl.let
                   SET zruseni_duvod_id = (SELECT min(id) FROM lkkl.lov_duvod_zruseni),
                       zruseno = now(), zrusil_id = %s
                   WHERE id = %s""",
                (zalozil, let_id),
            )
        return let_id

    return zalozit
