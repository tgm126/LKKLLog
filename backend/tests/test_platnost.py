"""Platnost záznamů číselníků (db/031): neplatný se nenabízí a nejde nově použít; staré vazby
zůstávají a let s nimi jde dál upravovat."""

import psycopg
import pytest

from .conftest import _id
from .test_akce import _novy


def _zneplatnit(conn, tabulka: str, sloupec: str, hodnota: str) -> None:
    conn.execute(f"UPDATE lkkl.{tabulka} SET platny = false WHERE {sloupec} = %s", (hodnota,))  # noqa: S608


def test_vyrazene_letadlo(conn, pilot, let):
    pilot_id, k = pilot
    stary = let("OK-2817", {"PIC": pilot_id})
    _zneplatnit(conn, "lov_letadlo", "rejstrik", "OK-2817")

    nabidky = k.get("/api/lety/nabidky").json()
    assert "OK-2817" not in {a["rejstrik"] for a in nabidky["letadla"]}

    odpoved = k.post(
        "/api/lety", json=_novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, akce="vzlet")
    )
    assert odpoved.status_code == 400
    assert odpoved.json()["detail"] == "Letadlo „OK-2817“ už neplatí – nejde použít."

    # naplánovaný let z doby, kdy letadlo platilo, jde dál odbavit
    assert k.post(f"/api/lety/{stary}/vzlet").status_code == 200


def test_neplatny_ucel_a_osoba(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    zak = osoba("Zak")
    _zneplatnit(conn, "lov_ucel", "kod", "NORMALNI")
    conn.execute("UPDATE lkkl.lov_osoba SET platny = false WHERE id = %s", (zak,))

    nabidky = k.get("/api/lety/nabidky").json()
    assert "NORMALNI" not in {u["kod"] for u in nabidky["ucely"]}
    assert zak not in {o["id"] for o in nabidky["osoby"]}

    ucel = k.post(
        "/api/lety", json=_novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, akce="vzlet")
    )
    assert ucel.status_code == 400
    assert ucel.json()["detail"] == "Účel „Normální“ už neplatí – nejde použít."
    conn.execute("UPDATE lkkl.lov_ucel SET platny = true WHERE kod = 'NORMALNI'")
    posadka = k.post(
        "/api/lety", json=_novy(conn, rejstrik="OK-2817", posadka={"PIC": zak}, akce="vzlet")
    )
    assert posadka.status_code == 400
    assert posadka.json()["detail"] == "Osoba „Jan Zak“ už neplatí – nejde použít."


def test_stara_vazba_zustava(conn, osoba, let):
    pilot = osoba("Pilot")
    let_id = let("OK-2817", {"PIC": pilot}, ucel="VYCVIK")
    _zneplatnit(conn, "lov_ucel", "kod", "VYCVIK")
    # úprava jiného údaje projde, nová vazba na neplatný záznam ne (i přímo v databázi)
    conn.execute("UPDATE lkkl.let SET pob = 2, ucel_id = ucel_id WHERE id = %s", (let_id,))
    normalni = _id(conn, "lov_ucel", "NORMALNI")
    conn.execute("UPDATE lkkl.let SET ucel_id = %s WHERE id = %s", (normalni, let_id))
    with (
        pytest.raises(psycopg.errors.RaiseException, match="Účel „Výcvik“ už neplatí"),
        conn.transaction(),
    ):
        conn.execute(
            "UPDATE lkkl.let SET ucel_id = %s WHERE id = %s",
            (_id(conn, "lov_ucel", "VYCVIK"), let_id),
        )


def test_vazby_ciselniku(conn, flotila):
    _zneplatnit(conn, "lov_typ", "kod", "L13")
    with (
        pytest.raises(psycopg.errors.RaiseException, match="Typ „L 13“ už neplatí"),
        conn.transaction(),
    ):
        conn.execute(
            """INSERT INTO lkkl.lov_letadlo (rejstrik, typ_id)
               SELECT 'OK-0001', id FROM lkkl.lov_typ WHERE kod = 'L13'"""
        )
