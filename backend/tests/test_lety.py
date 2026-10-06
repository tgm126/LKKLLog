"""Přehled letů dne a sluneční časy (docs/modul-lety.md)."""

from datetime import UTC, datetime

import pytest

from app import lety


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
                        CASE WHEN {pristani or "NULL"} IS NOT NULL
                             THEN (SELECT id FROM lkkl.lov_letiste WHERE kod = %(misto)s) END,
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


def test_den_a_slunce(prihlasit, osoba, flotila):
    osoba("Pilot")
    den = prihlasit("pilot@example.cz").get("/api/den", params={"den": "2026-10-06"}).json()
    assert den["den"] == "2026-10-06" and den["domovske"] == "LKKL"
    # Kladno 6. 10. 2026 (UTC): soumrak 04:38, východ 05:11, západ 16:31, konec soumraku 17:04.
    casy = {k: v[11:16] for k, v in den["slunce"].items()}
    assert casy == {"tb": "04:38", "sr": "05:11", "ss": "16:31", "te": "17:04"}


def test_lety_dne(prihlasit, osoba, let):
    pilot, zak = osoba("Pilot"), osoba("Zak")
    vzduch = let(
        "OK-2817",
        {"PIC": pilot, "ZAK": zak},
        ucel="VYCVIK",
        vzlet="now() - interval '10 minutes'",
        pob=None,
    )
    vlecna = let("OK-CRA", {"PIC": pilot}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": zak}, zpusob="VLEK", vlecny_let_id=vlecna)
    prelet = let(
        "OK-CRA",
        {"PIC": pilot},
        zpusob="VLASTNI",
        vzlet="now() - interval '2 hours'",
        pristani="now() - interval '1 hour'",
        misto_pristani="LKLT",
    )
    zruseny = let("OK-3819", {"PIC": pilot}, zrusit=True)
    vcera = let(
        "OK-3819",
        {"PIC": pilot},
        vzlet="now() - interval '30 hours'",
        pristani="now() - interval '29 hours'",
    )

    odpoved = prihlasit("pilot@example.cz").get("/api/lety").json()
    pasky = {p["id"]: p for p in odpoved["lety"]}
    assert vcera not in pasky
    assert {pasky[i]["stav"] for i in pasky} == {"VE_VZDUCHU", "NAPLANOVAN", "UKONCEN", "ZRUSEN"}

    v = pasky[vzduch]
    posadka = [(c["prijmeni"], c["funkce_kod"]) for c in v["posadka"]]
    assert posadka == [("Pilot", "PIC"), ("Zak", "ZAK")]
    assert v["pob"] is None  # u výcviku z posádky, na pásku se neukazuje
    assert v["ucel_kod"] == "VYCVIK" and v["zpusob_vzletu_kod"] == "NAVIJAK"
    assert v["misto_vzletu"] is None  # domovské se neuvádí
    assert v["varovani"] is None

    assert pasky[kluzak]["vlek_rejstrik"] == "OK-CRA" and pasky[kluzak]["vlecny_let_id"] == vlecna
    assert pasky[vlecna]["je_vlecny"] and pasky[vlecna]["vlek_rejstrik"] == "OK-3819"
    assert pasky[prelet]["misto_pristani"] == "LKLT" and pasky[prelet]["doba_uctovana_min"] == 60
    assert pasky[zruseny]["duvod_zruseni"] is not None


def test_ve_vzduchu_od_vcerejska(prihlasit, osoba, let):
    pilot = osoba("Pilot")
    nocni = let("OK-3819", {"PIC": pilot}, vzlet="now() - interval '30 hours'")
    pasek = prihlasit("pilot@example.cz").get("/api/lety").json()["lety"][0]
    assert pasek["id"] == nocni and pasek["varovani"].startswith("Přes maximální dobu letu (1°00")


def test_varovani():
    te = datetime(2026, 10, 6, 17, 4, tzinfo=UTC)
    ve_vzduchu = {"stav": "VE_VZDUCHU", "cas_vzletu": datetime(2026, 10, 6, 16, 0, tzinfo=UTC)}
    pozde = datetime(2026, 10, 6, 17, 10, tzinfo=UTC)
    assert lety.varovani({**ve_vzduchu, "max_doba_min": None}, pozde, te) == (
        "Po konci občanského soumraku (TE 17:04)"
    )
    assert lety.varovani({**ve_vzduchu, "max_doba_min": 45}, pozde, None) == (
        'Přes maximální dobu letu (45")'
    )
    assert lety.varovani({**ve_vzduchu, "max_doba_min": None}, te, te) is None
    assert lety.varovani({"stav": "UKONCEN"}, pozde, te) is None


def test_bez_prihlaseni(klient):
    assert klient().get("/api/lety").status_code == 401
    assert klient().get("/api/den").status_code == 401
