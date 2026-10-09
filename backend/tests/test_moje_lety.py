"""Moje lety: jen lety, kde je přihlášená osoba v posádce; dny s mými lety
(docs/modul-moje-lety.md)."""


def test_moje_lety(conn, pilot, osoba, let):
    pilot_id, k = pilot
    jiny, vlekar = osoba("Jiny"), osoba("Vlekar")
    muj = let("OK-2817", {"PIC": pilot_id})
    let("OK-3819", {"PIC": jiny})  # cizí
    # vlek: já jsem v kluzáku, vlečnou letí vlekař – pásek vleku je celý
    vlecna = let("OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": pilot_id}, zpusob="VLEK", vlecny_let_id=vlecna)
    # včera jako dozor (na zemi) – i to je můj let
    vcera = let(
        "OK-2817", {"PIC": jiny, "DOZOR": pilot_id}, ucel="VYCVIK_SOLO", pob=None,
        vzlet="now() - interval '1 day 2 hours'", pristani="now() - interval '1 day 1 hour'",
    )  # fmt: skip

    vsechny = {p["id"] for p in k.get("/api/lety").json()["lety"]}
    moje = {p["id"] for p in k.get("/api/lety?moje=true").json()["lety"]}
    assert moje == {muj, kluzak, vlecna} and moje < vsechny
    den_vcera = conn.execute("SELECT den FROM lkkl.v_let WHERE id = %s", (vcera,)).fetchone()["den"]
    vcerejsi = k.get(f"/api/lety?moje=true&den={den_vcera}").json()["lety"]
    assert [p["id"] for p in vcerejsi] == [vcera]

    dny = k.get("/api/lety/moje-dny").json()
    dnes = conn.execute("SELECT (now() AT TIME ZONE 'UTC')::date AS d").fetchone()["d"]
    assert dny == [den_vcera.isoformat(), dnes.isoformat()]
