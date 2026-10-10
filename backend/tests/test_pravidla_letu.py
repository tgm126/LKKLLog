"""Pravidla a výpočty přenesené z aplikace do databáze (db/035, 036)."""

import psycopg
import pytest

from app.lety import na_minuty

from .conftest import _id
from .test_akce import _novy


def _chyba(conn, sql: str, parametry=()) -> str:
    """Chyba z databáze; kontroly letu (odložené na konec transakce) se vyhodnotí hned."""
    with pytest.raises(psycopg.errors.RaiseException) as e, conn.transaction():
        conn.execute(sql, parametry)
        conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    return e.value.diag.message_primary


def _vlek(let, osoba, pilot: int, vzlet: str | None = None) -> tuple[int, int]:
    vlecna = let("OK-CRA", {"PIC": osoba("Vlekar")}, ucel=None, zpusob="VLASTNI", vzlet=vzlet)
    kluzak = let("OK-3819", {"PIC": pilot}, zpusob="VLEK", vzlet=vzlet, vlecny_let_id=vlecna)
    return kluzak, vlecna


TG = "INSERT INTO lkkl.let_tg (let_id, cas) VALUES (%s, now() - interval '5 minutes')"


def test_tg_jen_motorove(conn, osoba, let):
    pilot = osoba("Pilot")
    kluzak = let("OK-2817", {"PIC": pilot}, vzlet="now() - interval '20 minutes'")
    assert "T&G jde jen u motorového" in _chyba(conn, TG, (kluzak,))
    _, vlecna = _vlek(let, osoba, osoba("Druhy"), vzlet="now() - interval '20 minutes'")
    assert "ne u kluzáku ani vlečné" in _chyba(conn, TG, (vlecna,))


def test_vlek_jako_dvojice(conn, osoba, let):
    pilot = osoba("Pilot")
    kluzak, vlecna = _vlek(let, osoba, pilot)
    # vzlet jen jedné poloviny
    vzlet = "UPDATE lkkl.let SET vzlet_namereno = now() WHERE id = %s"
    assert "čas vzletu musí být stejný" in _chyba(conn, vzlet, (kluzak,))
    # zrušení naplánovaného vleku jen napůl
    zrusit = """UPDATE lkkl.let SET zruseni_duvod_id = (SELECT min(id) FROM lkkl.lov_duvod_zruseni),
                    zruseno = now() WHERE id = %s"""
    assert "ruší i obnovuje celý" in _chyba(conn, zrusit, (vlecna,))
    # vlekař zároveň v posádce kluzáku
    vlekar = conn.execute(
        "SELECT osoba_id FROM lkkl.posadka WHERE let_id = %s", (vlecna,)
    ).fetchone()["osoba_id"]
    pridat = "INSERT INTO lkkl.posadka (let_id, osoba_id, funkce_id) VALUES (%s, %s, %s)"
    zak = _id(conn, "lov_funkce", "ZAK")
    conn.execute(
        "UPDATE lkkl.let SET ucel_id = %s WHERE id = %s", (_id(conn, "lov_ucel", "VYCVIK"), kluzak)
    )
    conn.execute("UPDATE lkkl.let SET pob = NULL WHERE id = %s", (kluzak,))
    assert "vlekař nemůže být" in _chyba(conn, pridat, (kluzak, vlekar, zak))


def test_vlekar_mimo_posadku_z_pruvodce(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    data = _novy(
        conn,
        rejstrik="OK-3819",
        zpusob="VLEK",
        posadka={"PIC": pilot_id},
        pob=1,
        vlecna_id=conn.execute(
            "SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = 'OK-CRA'"
        ).fetchone()["id"],
        vlekar_id=pilot_id,
        akce="naplanovat",
    )
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 400
    assert odpoved.json()["detail"] == "Vlekař nemůže být zároveň v posádce kluzáku."


def test_uprava_vzletu_vleku_pro_oba(conn, pilot, osoba, let):
    pilot_id, k = pilot
    kluzak, vlecna = _vlek(let, osoba, pilot_id, vzlet="now() - interval '30 minutes'")
    verze = k.get(f"/api/lety/{kluzak}").json()["verze"]
    novy = conn.execute("SELECT now() - interval '40 minutes' AS t").fetchone()["t"]
    odpoved = k.post(f"/api/lety/{kluzak}", json={"verze": verze, "cas_vzletu": novy.isoformat()})
    assert odpoved.status_code == 200, odpoved.text
    casy = conn.execute(
        "SELECT cas_vzletu FROM lkkl.let WHERE id IN (%s, %s)", (kluzak, vlecna)
    ).fetchall()
    assert [r["cas_vzletu"] for r in casy] == [na_minuty(novy)] * 2


def test_zpusob_vzletu_podle_kategorie(conn, osoba, let):
    pilot = osoba("Pilot")
    motor = let("OK-CRA", {"PIC": pilot}, zpusob="VLASTNI")
    navijak = _id(conn, "lov_zpusob_vzletu", "NAVIJAK")
    sql = "UPDATE lkkl.let SET zpusob_vzletu_id = %s WHERE id = %s"
    assert "ostatní letadla vlastním pohonem" in _chyba(conn, sql, (navijak, motor))
    kluzak = let("OK-2817", {"PIC": pilot})
    assert "kluzák vzlétá navijákem" in _chyba(
        conn, sql, (_id(conn, "lov_zpusob_vzletu", "VLASTNI"), kluzak)
    )


def test_cas_ne_v_budoucnosti(conn, pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-2817", {"PIC": pilot_id})
    assert _chyba(
        conn,
        "UPDATE lkkl.let SET vzlet_namereno = now() + interval '1 hour' WHERE id = %s",
        (let_id,),
    ) == ("Čas nesmí být v budoucnosti.")
    data = _novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, pob=1, akce="probehly")
    budoucnost = conn.execute("SELECT now() + interval '1 hour' AS t").fetchone()["t"]
    odpoved = k.post(
        "/api/lety",
        json={**data, "cas_vzletu": budoucnost.isoformat(), "cas_pristani": budoucnost.isoformat()},
    )
    assert odpoved.status_code == 400 and odpoved.json()["detail"] == "Čas nesmí být v budoucnosti."


def test_druh_provozu_a_poloha(conn, pilot, osoba, let):
    pilot_id, k = pilot
    kluzak, vlecna = _vlek(let, osoba, pilot_id)
    prelet = let(
        "OK-CRA",
        {"PIC": pilot_id},
        zpusob="VLASTNI",
        vzlet="now() - interval '3 hours'",
        pristani="now() - interval '2 hours'",
        misto_pristani="LKLT",
    )
    druh = {p["id"]: p["druh_provozu"] for p in k.get("/api/lety").json()["lety"]}
    assert druh == {kluzak: "PLACHTARSKY", vlecna: "PLACHTARSKY", prelet: "MOTOROVY"}
    letadla = {a["rejstrik"]: a for a in k.get("/api/lety/nabidky").json()["letadla"]}
    assert letadla["OK-CRA"]["poloha"] == "LKLT" and letadla["OK-2817"]["poloha"] is None
    # výchozí místo vzletu nového letu (db/037): letiště posledního přistání
    assert letadla["OK-CRA"]["poloha_letiste_id"] == _id(conn, "lov_letiste", "LKLT")
    assert letadla["OK-CRA"]["poloha_popis"] is None


def test_prekrocena_doba(conn, pilot, osoba, let):
    pilot_id, k = pilot
    conn.execute("UPDATE lkkl.lov_letadlo SET max_doba_min = 30 WHERE rejstrik = 'OK-CRA'")
    dlouho = let(
        "OK-CRA", {"PIC": pilot_id}, zpusob="VLASTNI", vzlet="now() - interval '40 minutes'"
    )
    kratce = let("OK-2817", {"PIC": osoba("Druha")}, vzlet="now() - interval '40 minutes'")
    prekroceno = {
        r["id"]: r["prekrocena_doba"]
        for r in conn.execute("SELECT id, prekrocena_doba FROM lkkl.v_let").fetchall()
    }
    assert prekroceno == {dlouho: True, kratce: False}
    pasky = {p["id"]: p["varovani"] or "" for p in k.get("/api/lety").json()["lety"]}
    assert 'Přes maximální dobu letu (30")' in pasky[dlouho]
    assert "maximální" not in pasky[kratce]


def test_souhrn_dne(conn, pilot, osoba, let):
    pilot_id, k = pilot
    vlecna = let(
        "OK-CRA",
        {"PIC": osoba("Vlekar")},
        ucel=None,
        zpusob="VLASTNI",
        vzlet="now() - interval '3 hours'",
        pristani="now() - interval '170 minutes'",
    )
    let(
        "OK-3819",
        {"PIC": pilot_id},
        zpusob="VLEK",
        vzlet="now() - interval '3 hours'",
        pristani="now() - interval '2 hours'",
        vlecny_let_id=vlecna,
    )
    let(
        "OK-CRA",
        {"PIC": pilot_id},
        zpusob="VLASTNI",
        vzlet="now() - interval '90 minutes'",
        pristani="now() - interval '60 minutes'",
    )
    let(
        "OK-2817",
        {"PIC": pilot_id},
        zpusob="NAVIJAK",
        vzlet="now() - interval '50 minutes'",
        pristani="now() - interval '40 minutes'",
    )
    let("OK-2817", {"PIC": pilot_id})  # naplánovaný se nepočítá
    souhrn = k.get("/api/lety").json()["souhrn"]
    assert sorted(
        (r["druh_provozu"], r["rejstrik"], r["je_vlecny"], r["lety"], r["minut"], r["navijaky"])
        for r in souhrn
    ) == [
        ("MOTOROVY", "OK-CRA", False, 1, 30, 0),
        ("PLACHTARSKY", "OK-2817", False, 1, 10, 1),
        ("PLACHTARSKY", "OK-3819", False, 1, 60, 0),
        ("PLACHTARSKY", "OK-CRA", True, 1, 10, 0),
    ]


def _casy(conn, let_id: int) -> dict:
    return conn.execute(
        """SELECT to_char(cas_vzletu AT TIME ZONE 'UTC', 'HH24:MI:SS') AS vzlet,
                  to_char(cas_pristani AT TIME ZONE 'UTC', 'HH24:MI:SS') AS pristani, doba_min
           FROM lkkl.let WHERE id = %s""",
        (let_id,),
    ).fetchone()


@pytest.mark.parametrize(
    ("vzlet", "pristani", "ocekavane"),
    [
        # dřív 10:00–10:10 (useknuté), ale doba 11
        ("10:00:20", "10:10:50", {"vzlet": "10:00:00", "pristani": "10:11:00", "doba_min": 11}),
        # zaokrouhlení každého času zvlášť by dalo 10:00–10:11 a dobu 11, čistý čas je 10:02
        ("10:00:29", "10:10:31", {"vzlet": "10:00:00", "pristani": "10:10:00", "doba_min": 10}),
        ("10:00:30", "10:10:29", {"vzlet": "10:01:00", "pristani": "10:11:00", "doba_min": 10}),
        # krátký let: nejméně 1 minuta, přistání = vzlet + 1
        ("10:00:40", "10:00:55", {"vzlet": "10:01:00", "pristani": "10:02:00", "doba_min": 1}),
    ],
)
def test_casy_na_minuty(conn, osoba, let, vzlet, pristani, ocekavane):
    """Vzlet na nejbližší minutu, doba z naměřeného času, přistání = vzlet + doba (3.6)."""
    let_id = let(
        "OK-2817", {"PIC": osoba("Pilot")},
        vzlet=f"timestamptz '2026-10-01 {vzlet}+00'",
        pristani=f"timestamptz '2026-10-01 {pristani}+00'",
    )  # fmt: skip
    assert _casy(conn, let_id) == ocekavane


def test_uprava_jednoho_casu_drzi_zobrazeny_druhy(conn, osoba, prihlasit, let):
    """Upravené přistání: vzlet zůstane, jak byl zobrazený, doba = rozdíl zobrazených časů."""
    let_id = let(
        "OK-2817", {"PIC": osoba("Pilot")},
        vzlet="timestamptz '2026-10-01 10:00:40+00'",
        pristani="timestamptz '2026-10-01 10:10:10+00'",
    )  # fmt: skip
    k = prihlasit("pilot@example.cz")
    verze = k.get(f"/api/lety/{let_id}").json()["verze"]
    d = k.post(
        f"/api/lety/{let_id}",
        json={"verze": verze, "cas_pristani": "2026-10-01T10:15:00Z"},
    )
    assert d.status_code == 200, d.text
    assert _casy(conn, let_id) == {"vzlet": "10:01:00", "pristani": "10:15:00", "doba_min": 14}
