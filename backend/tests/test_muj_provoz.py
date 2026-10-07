"""Můj provoz: letiště a osoby v provozu na dnešek pro relaci (docs/modul-muj-provoz.md)."""

from .test_akce import _novy


def _misto(conn, let_id: int) -> dict:
    return conn.execute(
        "SELECT misto_vzletu, misto_pristani FROM lkkl.v_let WHERE id = %s", (let_id,)
    ).fetchone()


def test_letiste_na_dnesek(conn, pilot, flotila):
    """Zvolené letiště: hlavička, výchozí místo nového letu i přistání, pásky."""
    pilot_id, k = pilot
    assert k.get("/api/muj-provoz").json() == {
        "letiste": {"id": k.get("/api/den").json()["letiste"]["id"], "kod": "LKKL",
                    "nazev": "Kladno", "domovske": True},
        "osoby": [],
    }  # fmt: skip
    letnany = conn.execute("SELECT id FROM lkkl.lov_letiste WHERE kod = 'LKLT'").fetchone()["id"]
    provoz = k.post("/api/muj-provoz/letiste", json={"letiste_id": letnany}).json()
    assert provoz["letiste"]["kod"] == "LKLT" and not provoz["letiste"]["domovske"]

    den = k.get("/api/den").json()
    assert den["letiste"]["kod"] == "LKLT"

    data = _novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, pob=1, akce="vzlet")
    let_id = k.post("/api/lety", json=data).json()["let_id"]
    assert _misto(conn, let_id)["misto_vzletu"] == "LKLT"
    assert k.post(f"/api/lety/{let_id}/pristani").status_code == 200
    assert _misto(conn, let_id) == {"misto_vzletu": "LKLT", "misto_pristani": "LKLT"}

    # Na pásku se moje letiště neuvádí; po návratu na domovské ano.
    pasek = next(p for p in k.get("/api/lety").json()["lety"] if p["id"] == let_id)
    assert pasek["misto_vzletu"] is None
    k.post("/api/muj-provoz/letiste", json={"letiste_id": None})
    pasek = next(p for p in k.get("/api/lety").json()["lety"] if p["id"] == let_id)
    assert pasek["misto_vzletu"] == "LKLT"


def test_jen_dnes_a_jen_pro_relaci(conn, pilot, osoba, prihlasit, flotila):
    pilot_id, k = pilot
    zak = osoba("Zak", ucet=False)
    letnany = conn.execute("SELECT id FROM lkkl.lov_letiste WHERE kod = 'LKLT'").fetchone()["id"]
    k.post("/api/muj-provoz/letiste", json={"letiste_id": letnany})
    provoz = k.post("/api/muj-provoz/osoby", json={"osoba_id": zak, "ma": True}).json()
    assert provoz["osoby"] == [zak]

    # Jiné zařízení (relace) téhož uživatele nastavení nemá.
    druhe = prihlasit("pilot@example.cz").get("/api/muj-provoz").json()
    assert druhe["letiste"]["kod"] == "LKKL" and druhe["osoby"] == []

    # Včerejší nastavení se neuplatní; první uložení dnes ho přepíše i s osobami.
    conn.execute("UPDATE lkkl.relace_provoz SET den = den - 1")
    vcera = k.get("/api/muj-provoz").json()
    assert vcera["letiste"]["kod"] == "LKKL" and vcera["osoby"] == []
    provoz = k.post("/api/muj-provoz/osoby", json={"osoba_id": pilot_id, "ma": True}).json()
    assert provoz["osoby"] == [pilot_id] and provoz["letiste"]["kod"] == "LKKL"

    provoz = k.post("/api/muj-provoz/osoby", json={"osoba_id": pilot_id, "ma": False}).json()
    assert provoz["osoby"] == []
    k.post("/api/muj-provoz/osoby", json={"osoba_id": zak, "ma": True})
    assert k.post("/api/muj-provoz/osoby/zrusit").json()["osoby"] == []


def test_odhlaseni_smaze_nastaveni(conn, pilot, osoba):
    _, k = pilot
    k.post("/api/muj-provoz/osoby", json={"osoba_id": osoba("Zak", ucet=False), "ma": True})
    assert k.post("/api/odhlaseni").status_code == 204
    pocet = conn.execute(
        """SELECT (SELECT count(*) FROM lkkl.relace_provoz)
                + (SELECT count(*) FROM lkkl.relace_provoz_osoba) AS n"""
    ).fetchone()["n"]
    assert pocet == 0
