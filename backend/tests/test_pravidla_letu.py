"""Pravidla a výpočty přenesené z aplikace do databáze (db/035, 036)."""

import psycopg
import pytest

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
    vzlet = "UPDATE lkkl.let SET cas_vzletu = now() WHERE id = %s"
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
    assert [r["cas_vzletu"] for r in casy] == [novy, novy]


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
        conn, "UPDATE lkkl.let SET cas_vzletu = now() + interval '1 hour' WHERE id = %s", (let_id,)
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
    poloha = {a["rejstrik"]: a["poloha"] for a in k.get("/api/lety/nabidky").json()["letadla"]}
    assert poloha["OK-CRA"] == "LKLT" and poloha["OK-2817"] is None


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
    let("OK-2817", {"PIC": pilot_id})  # naplánovaný se nepočítá
    souhrn = k.get("/api/lety").json()["souhrn"]
    assert sorted(
        (r["druh_provozu"], r["rejstrik"], r["je_vlecny"], r["lety"], r["minut"]) for r in souhrn
    ) == [
        ("MOTOROVY", "OK-CRA", False, 1, 30),
        ("PLACHTARSKY", "OK-3819", False, 1, 60),
        ("PLACHTARSKY", "OK-CRA", True, 1, 10),
    ]
