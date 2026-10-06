"""Akce letu (vzlet, přistání, T&G, Zpět) a nový let z průvodce (docs/modul-lety.md)."""

import pytest

from app.lety import PREKRYV

from .conftest import _id


def _stav(conn, let_id: int) -> dict:
    return conn.execute(
        """SELECT stav, cas_vzletu, cas_pristani, misto_pristani, pocet_pristani, pob,
                  platce_id, plati_aeroklub, vlecny_let_id
           FROM lkkl.v_let WHERE id = %s""",
        (let_id,),
    ).fetchone()


@pytest.fixture
def pilot(osoba, prihlasit):
    """Přihlášený pilot (id, klient)."""
    pilot_id = osoba("Pilot")
    return pilot_id, prihlasit("pilot@example.cz")


def test_vzlet_jen_jednou_a_zpet(conn, pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-2817", {"PIC": pilot_id})
    odpoved = k.post(f"/api/lety/{let_id}/vzlet")
    assert odpoved.status_code == 200 and odpoved.json()["rejstrik"] == "OK-2817"
    assert _stav(conn, let_id)["stav"] == "VE_VZDUCHU"

    znovu = k.post(f"/api/lety/{let_id}/vzlet")
    assert znovu.status_code == 409 and znovu.json()["detail"].startswith("OK-2817: Už vzlétl v")

    assert k.post(f"/api/lety/{let_id}/zpet", json={"akce": "vzlet"}).status_code == 200
    assert _stav(conn, let_id)["stav"] == "NAPLANOVAN"


def test_vzlet_vleku_pro_oba(conn, pilot, osoba, let):
    pilot_id, k = pilot
    vlekar = osoba("Vlekar")
    vlecna = let("OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": pilot_id}, zpusob="VLEK", vlecny_let_id=vlecna)
    assert k.post(f"/api/lety/{vlecna}/vzlet").status_code == 200  # stisk u kterékoli z dvojice
    assert _stav(conn, kluzak)["cas_vzletu"] == _stav(conn, vlecna)["cas_vzletu"] is not None
    assert k.post(f"/api/lety/{kluzak}/zpet", json={"akce": "vzlet"}).status_code == 200
    assert _stav(conn, vlecna)["stav"] == _stav(conn, kluzak)["stav"] == "NAPLANOVAN"


def test_tg_pristani_a_zpet(conn, pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-CRA", {"PIC": pilot_id}, zpusob="VLASTNI", vzlet="now()")
    # (V transakci testu má každé T&G stejný čas – proto jen jedno; Zpět ho vrátí.)
    assert k.post(f"/api/lety/{let_id}/tg").status_code == 200
    assert k.post(f"/api/lety/{let_id}/zpet", json={"akce": "tg"}).status_code == 200
    assert k.post(f"/api/lety/{let_id}/tg").status_code == 200
    odpoved = k.post(f"/api/lety/{let_id}/pristani")
    assert odpoved.status_code == 200
    stav = _stav(conn, let_id)
    assert stav["stav"] == "UKONCEN" and stav["misto_pristani"] == "LKKL"
    assert stav["pocet_pristani"] == 2  # T&G + přistání

    znovu = k.post(f"/api/lety/{let_id}/pristani")
    assert znovu.status_code == 409 and "Už přistál" in znovu.json()["detail"]
    assert k.post(f"/api/lety/{let_id}/zpet", json={"akce": "pristani"}).status_code == 200
    stav = _stav(conn, let_id)
    assert stav["stav"] == "VE_VZDUCHU" and stav["misto_pristani"] is None


def test_tg_jen_motorove(pilot, let):
    pilot_id, k = pilot
    kluzak = let("OK-2817", {"PIC": pilot_id}, vzlet="now()")
    assert k.post(f"/api/lety/{kluzak}/tg").status_code == 409


def test_zpet_jen_hned(pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '2 minutes'")
    odpoved = k.post(f"/api/lety/{let_id}/zpet", json={"akce": "vzlet"})
    assert odpoved.status_code == 409 and odpoved.json()["detail"] == "OK-2817: vrátit už nejde."


def test_prekryv(pilot, let):
    pilot_id, k = pilot
    let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '10 minutes'")
    druhy = let("OK-2817", {"PIC": pilot_id})
    odpoved = k.post(f"/api/lety/{druhy}/vzlet")
    assert odpoved.status_code == 409 and odpoved.json()["detail"] == PREKRYV


# --- nový let z průvodce --------------------------------------------------------------------


def _novy(conn, **udaje) -> dict:
    """Tělo požadavku POST /api/lety; letadlo, účel a způsob podle kódu."""
    letadlo = conn.execute(
        "SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = %s", (udaje.pop("rejstrik"),)
    ).fetchone()["id"]
    return {
        "letadlo_id": letadlo,
        "ucel_id": _id(conn, "lov_ucel", udaje.pop("ucel", "NORMALNI")),
        "zpusob_vzletu_id": _id(conn, "lov_zpusob_vzletu", udaje.pop("zpusob", "NAVIJAK")),
        "posadka": [
            {"osoba_id": o, "funkce_id": _id(conn, "lov_funkce", f)}
            for f, o in udaje.pop("posadka").items()
        ],
        **udaje,
    }


def test_novy_let_vzlet_ted(conn, pilot, flotila):
    pilot_id, k = pilot
    data = _novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, pob=1, akce="vzlet")
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 200, odpoved.text
    stav = _stav(conn, odpoved.json()["let_id"])
    assert stav["stav"] == "VE_VZDUCHU" and stav["platce_id"] == pilot_id  # plátce = PIC


def test_novy_let_vycvik(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    zak = osoba("Zak")
    data = _novy(
        conn, rejstrik="OK-2817", ucel="VYCVIK", posadka={"PIC": pilot_id, "ZAK": zak},
        akce="naplanovat",
    )  # fmt: skip
    # Bez úlohy to databáze odmítne (srozumitelně, bez „Let 12:“).
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 400
    assert odpoved.json()["detail"] == "u tohoto účelu je úloha povinná."

    osnova = conn.execute(
        """INSERT INTO lkkl.lov_osnova (kod, nazev, poradi) VALUES ('ZAKLAD', 'Základní', 10)
           RETURNING id"""
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO lkkl.lov_osnova_ucel (osnova_id, ucel_id) VALUES (%s, %s)",
        (osnova, _id(conn, "lov_ucel", "VYCVIK")),
    )
    uloha = conn.execute(
        """INSERT INTO lkkl.lov_uloha (kod, nazev, poradi, osnova_id)
           VALUES ('B3', 'B3 – Okruhy', 10, %s) RETURNING id""",
        (osnova,),
    ).fetchone()["id"]
    odpoved = k.post("/api/lety", json={**data, "uloha_id": uloha})
    assert odpoved.status_code == 200, odpoved.text
    stav = _stav(conn, odpoved.json()["let_id"])
    assert stav["stav"] == "NAPLANOVAN" and stav["platce_id"] == zak  # u výcviku platí žák
    assert stav["pob"] == 2  # z posádky


def test_novy_probehly_aerovlek(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    vlekar = osoba("Vlekar")
    casy = conn.execute(
        """SELECT now() - interval '50 minutes' AS vzlet, now() - interval '10 minutes' AS pristani,
                  now() - interval '40 minutes' AS vlecna"""
    ).fetchone()
    data = _novy(
        conn,
        rejstrik="OK-3819",
        zpusob="VLEK",
        posadka={"PIC": pilot_id},
        pob=1,
        vlecna_id=conn.execute(
            "SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = 'OK-CRA'"
        ).fetchone()["id"],
        vlekar_id=vlekar,
        plati_aeroklub=True,
        akce="probehly",
        cas_vzletu=casy["vzlet"].isoformat(),
        cas_pristani=casy["pristani"].isoformat(),
        cas_pristani_vlecne=casy["vlecna"].isoformat(),
    )
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 200, odpoved.text
    kluzak = _stav(conn, odpoved.json()["let_id"])
    vlecna = _stav(conn, kluzak["vlecny_let_id"])
    assert kluzak["stav"] == vlecna["stav"] == "UKONCEN"
    assert kluzak["cas_vzletu"] == vlecna["cas_vzletu"] == casy["vzlet"]
    assert vlecna["cas_pristani"] == casy["vlecna"] and vlecna["pob"] == 1
    assert kluzak["plati_aeroklub"] and vlecna["plati_aeroklub"]

    # Bez času přistání vlečné proběhlý aerovlek nejde.
    bez = {**data, "cas_pristani_vlecne": None}
    assert k.post("/api/lety", json=bez).status_code == 400


def test_nabidky(conn, pilot, let):
    pilot_id, k = pilot
    let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '5 minutes'")
    nabidky = k.get("/api/lety/nabidky").json()
    letadla = {a["rejstrik"]: a for a in nabidky["letadla"]}
    assert letadla["OK-2817"]["leti_od"] is not None and letadla["OK-2817"]["nedavni"] == [pilot_id]
    assert letadla["OK-CRA"]["vlecne"]
    ucely = {u["kod"]: u for u in nabidky["ucely"]}
    assert [f["kod"] for f in ucely["VYCVIK"]["funkce"]] == ["ZAK"]
    assert ucely["NORMALNI"]["funkce"] == []
    assert nabidky["zpusob_kluzaku"] == "NAVIJAK"
