"""Letadla: právo spravuje letadla a přepínač mimo provoz (docs/modul-letadla.md)."""


def test_prava_k_letadlum(osoba, prihlasit, flotila):
    osoba("Admin", admin=True)
    osoba("Technik", spravuje_letadla=True)
    pilot = osoba("Pilot")
    assert prihlasit("pilot@example.cz").get("/api/letadla").status_code == 403

    technik = prihlasit("technik@example.cz")
    assert technik.get("/api/ja").json()["prava"]["spravuje_letadla"]
    assert [a["rejstrik"] for a in technik.get("/api/letadla").json()] == [
        "OK-2817", "OK-3819", "OK-CRA",
    ]  # fmt: skip
    # Právo přiděluje jen admin.
    odpoved = technik.post(f"/api/ucty/{pilot}", json={"spravuje_letadla": True})
    assert odpoved.status_code == 403
    admin = prihlasit("admin@example.cz")
    assert admin.get("/api/ja").json()["prava"]["spravuje_letadla"]  # admin má vše
    odpoved = admin.post(f"/api/ucty/{pilot}", json={"spravuje_letadla": True})
    assert odpoved.status_code == 200 and odpoved.json()["spravuje_letadla"]


def test_mimo_provoz(conn, osoba, prihlasit, flotila):
    osoba("Technik", spravuje_letadla=True)
    k = prihlasit("technik@example.cz")
    letadlo = next(a for a in k.get("/api/letadla").json() if a["rejstrik"] == "OK-3819")
    assert not letadlo["mimo_provoz"]

    odpoved = k.post(f"/api/letadla/{letadlo['id']}/mimo-provoz", json={"mimo_provoz": True})
    assert odpoved.status_code == 200 and odpoved.json()["mimo_provoz"]
    nabidka = {a["rejstrik"]: a for a in k.get("/api/lety/nabidky").json()["letadla"]}
    assert nabidka["OK-3819"]["mimo_provoz"]  # v průvodci vidět, ale nejde vybrat

    # Změna se zapíše do auditu (kdo a kdy).
    zmena = conn.execute(
        """SELECT kdo, popis FROM lkkl.v_audit
           WHERE tabulka = 'lov_letadlo' AND operace = 'UPDATE' AND klic ->> 'id' = %s""",
        (str(letadlo["id"]),),
    ).fetchone()
    assert zmena == {"kdo": "Jan Technik", "popis": "mimo provoz ne → ano"}

    assert k.post("/api/letadla/999999/mimo-provoz", json={"mimo_provoz": True}).status_code == 404
