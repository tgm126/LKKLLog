"""Databáze pro klikací testy (Playwright): lkkllog_e2e sestavená ze skriptů db/, dvě osoby
s účty, letadla, letiště a dnešní lety ve všech stavech.

Spouští ji frontend/playwright.config.ts před startem serveru:
    uv run python -m tests.e2e_priprava
Data uživatele (databáze lkkllog) nikdy nepoužívá.
"""

import os

import psycopg

from app import bezpecnost, migrace

ZAKLAD = os.environ.get("LKKL_E2E_ZAKLAD", "postgresql://lkkllog:lkkllog@127.0.0.1:5432")
DATABAZE = "lkkllog_e2e"
HESLO_ADMINA = "heslo-pro-e2e-test"  # noqa: S105 – jen testovací databáze

FLOTILA = """
INSERT INTO lkkl.lov_kategorie (kod, nazev, poradi)
VALUES ('KLUZAK', 'Kluzák', 10), ('LETOUN', 'Letoun', 30);

INSERT INTO lkkl.lov_typ (kod, nazev, poradi, kategorie_id, pocet_mist)
SELECT v.kod, v.nazev, v.poradi, k.id, v.mist
FROM (VALUES ('L13', 'L 13', 10, 'KLUZAK', 2), ('ASW20', 'ASW 20', 20, 'KLUZAK', 1),
             ('Z126', 'Z 126', 30, 'LETOUN', 2), ('Z526', 'Z 526', 40, 'LETOUN', 2))
     AS v(kod, nazev, poradi, kat, mist)
JOIN lkkl.lov_kategorie k ON k.kod = v.kat;

INSERT INTO lkkl.lov_letadlo (rejstrik, typ_id, vlecne, max_doba_min)
SELECT v.rejstrik, t.id, v.vlecne, v.max_doba
FROM (VALUES ('OK-2817', 'L13', false, NULL), ('OK-3819', 'L13', false, NULL),
             ('OK-6722', 'ASW20', false, NULL), ('OK-MFV', 'Z126', false, 90),
             ('OK-CRA', 'Z526', true, NULL)) AS v(rejstrik, typ, vlecne, max_doba)
JOIN lkkl.lov_typ t ON t.kod = v.typ;

INSERT INTO lkkl.lov_letiste (kod, nazev, domovske, zem_sirka, zem_delka, poradi)
VALUES ('LKKL', 'Kladno', true, 50.1128, 14.0897, 10),
       ('LKLT', 'Letňany', false, 50.1314, 14.5257, 20);
"""


def _let(c, zalozil: int, posadka: dict[str, int], **udaje) -> int:
    """Let s posádkou; časy jako SQL výrazy (např. "now() - interval '1 hour'")."""
    vzlet, pristani = udaje.get("vzlet", "NULL"), udaje.get("pristani", "NULL")
    let_id = c.execute(
        f"""INSERT INTO lkkl.let (letadlo_id, ucel_id, zpusob_vzletu_id, vlecny_let_id,
                cas_vzletu, cas_pristani, misto_pristani_id, pocet_pristani, pob,
                plati_aeroklub, zalozil_id)
            VALUES ((SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = %(rejstrik)s),
                    (SELECT id FROM lkkl.lov_ucel WHERE kod = %(ucel)s),
                    (SELECT id FROM lkkl.lov_zpusob_vzletu WHERE kod = %(zpusob)s),
                    %(vlecny)s, {vzlet}, {pristani},
                    CASE WHEN {pristani} IS NOT NULL
                         THEN (SELECT id FROM lkkl.lov_letiste WHERE kod = %(misto)s) END,
                    CASE WHEN {pristani} IS NOT NULL THEN %(pristani_celkem)s END,
                    %(pob)s, true, %(zalozil)s)
            RETURNING id""",  # noqa: S608 – pevné výrazy z tohoto souboru
        {
            "rejstrik": udaje["rejstrik"],
            "ucel": udaje.get("ucel", "NORMALNI"),
            "zpusob": udaje.get("zpusob", "NAVIJAK"),
            "vlecny": udaje.get("vlecny_let_id"),
            "misto": udaje.get("misto_pristani", "LKKL"),
            "pristani_celkem": udaje.get("pocet_pristani", 1),
            "pob": udaje.get("pob", 1),
            "zalozil": zalozil,
        },
    ).fetchone()[0]
    for funkce, osoba_id in posadka.items():
        c.execute(
            """INSERT INTO lkkl.posadka (let_id, osoba_id, funkce_id)
               VALUES (%s, %s, (SELECT id FROM lkkl.lov_funkce WHERE kod = %s))""",
            (let_id, osoba_id, funkce),
        )
    return let_id


def lety(c, admin: int, nova: int) -> None:
    """Dnešní lety ve všech stavech (pásky v přehledu). Ve vzduchu létají piloti bez účtu,
    aby admin a Nela mohli v testech vzlétnout (osoba nesmí letět ve dvou letech zároveň)."""
    petr, olga = (
        c.execute(
            "INSERT INTO lkkl.lov_osoba (jmeno, prijmeni) VALUES (%s, %s) RETURNING id", jmeno
        ).fetchone()[0]
        for jmeno in (("Petr", "Pilot"), ("Olga", "Pilotka"))
    )
    _let(c, admin, {"PIC": petr}, rejstrik="OK-2817", pob=2,
         vzlet="now() - interval '12 minutes'")  # fmt: skip
    mfv = _let(
        c,
        admin,
        {"PIC": olga},
        rejstrik="OK-MFV",
        zpusob="VLASTNI",
        vzlet="now() - interval '2 hours'",
    )  # fmt: skip  – přes max. dobu
    c.execute("INSERT INTO lkkl.let_tg VALUES (%s, now() - interval '1 hour')", (mfv,))
    _let(c, admin, {"PIC": nova}, rejstrik="OK-3819")
    vlecna = _let(c, admin, {"PIC": admin}, rejstrik="OK-CRA", ucel=None, zpusob="VLASTNI")
    _let(c, admin, {"PIC": nova}, rejstrik="OK-6722", zpusob="VLEK", vlecny_let_id=vlecna)
    _let(c, admin, {"PIC": admin}, rejstrik="OK-CRA", zpusob="VLASTNI", misto_pristani="LKLT",
         pocet_pristani=3, vzlet="now() - interval '4 hours'",
         pristani="now() - interval '3 hours 15 minutes'")  # fmt: skip
    _let(c, admin, {"PIC": nova}, rejstrik="OK-3819", vzlet="now() - interval '3 hours'",
         pristani="now() - interval '2 hours 38 minutes'")  # fmt: skip
    zruseny = _let(c, admin, {"PIC": nova}, rejstrik="OK-2817")
    c.execute(
        """UPDATE lkkl.let SET zruseni_duvod_id = (SELECT min(id) FROM lkkl.lov_duvod_zruseni),
                              zruseno = now(), zrusil_id = %s
           WHERE id = %s""",
        (admin, zruseny),
    )


def pripravit() -> None:
    with psycopg.connect(f"{ZAKLAD}/lkkllog", autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DATABAZE,)).fetchone():
            c.execute(f"CREATE DATABASE {DATABAZE}")
    with psycopg.connect(f"{ZAKLAD}/{DATABAZE}", autocommit=True) as c:
        c.execute("DROP SCHEMA IF EXISTS lkkl CASCADE")
        migrace.provest(c)
        with c.transaction():
            admin = c.execute(
                """INSERT INTO lkkl.lov_osoba (jmeno, prijmeni, email)
                   VALUES ('Adam', 'Admin', 'admin@example.cz') RETURNING id"""
            ).fetchone()[0]
            c.execute(
                "INSERT INTO lkkl.ucet (osoba_id, heslo_hash, admin) VALUES (%s, %s, true)",
                (admin, bezpecnost.otisk_hesla(HESLO_ADMINA)),
            )
            nova = c.execute(
                """INSERT INTO lkkl.lov_osoba (jmeno, prijmeni, email)
                   VALUES ('Nela', 'Nová', 'nova@example.cz') RETURNING id"""
            ).fetchone()[0]
            c.execute("INSERT INTO lkkl.ucet (osoba_id) VALUES (%s)", (nova,))
            c.execute(FLOTILA)
            lety(c, admin, nova)


if __name__ == "__main__":
    pripravit()
