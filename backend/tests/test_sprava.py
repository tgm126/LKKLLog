"""Správa systému – jen admin (docs/modul-sprava.md): smazání letů dne a nastavení."""

from .conftest import HESLO


def test_jen_admin(osoba, prihlasit, klient):
    osoba("Pilot")
    osoba("Admin", admin=True)
    pilot = prihlasit("pilot@example.cz")
    for cesta in ("/api/sprava/dny-s-lety", "/api/sprava/nastaveni"):
        assert pilot.get(cesta).status_code == 403
    assert pilot.post("/api/sprava/smazat-den", json={"den": "2026-10-07"}).status_code == 403
    # admin přihlášený jen ke čtení nesmí nic měnit
    k = klient()
    odpoved = k.post(
        "/api/prihlaseni", json={"email": "admin@example.cz", "heslo": HESLO, "jen_cteni": True}
    )
    assert odpoved.status_code == 200
    assert k.post("/api/sprava/nastaveni", json={"testovaci_provoz": False}).status_code == 403


def test_smazat_den(conn, osoba, prihlasit, let):
    osoba("Admin", admin=True)
    pilot = osoba("Pilot")
    let("OK-2817", {"PIC": pilot}, vzlet="now() - interval '10 minutes'")
    let("OK-3819", {"PIC": pilot})
    let(
        "OK-3819",
        {"PIC": pilot},
        vzlet="now() - interval '30 hours'",
        pristani="now() - interval '29 hours'",
    )
    k = prihlasit("admin@example.cz")
    dny = {d["den"]: d["lety"] for d in k.get("/api/sprava/dny-s-lety").json()}
    dnes = conn.execute("SELECT (now() AT TIME ZONE 'UTC')::date AS d").fetchone()["d"].isoformat()
    assert dny[dnes] == 2 and len(dny) == 2

    odpoved = k.post("/api/sprava/smazat-den", json={"den": dnes})
    assert odpoved.status_code == 200, odpoved.text
    assert odpoved.json() == {"den": dnes, "smazano": 2}
    assert dnes not in {d["den"] for d in k.get("/api/sprava/dny-s-lety").json()}
    # v auditu je, kdo mazal
    kdo = conn.execute(
        """SELECT DISTINCT o.prijmeni FROM lkkl.audit a JOIN lkkl.lov_osoba o ON o.id = a.osoba_id
           WHERE a.tabulka = 'let' AND a.operace = 'DELETE'"""
    ).fetchall()
    assert [r["prijmeni"] for r in kdo] == ["Admin"]


def test_nastaveni(osoba, prihlasit):
    osoba("Admin", admin=True)
    k = prihlasit("admin@example.cz")
    assert k.get("/api/sprava/nastaveni").json() == {"testovaci_provoz": True}
    odpoved = k.post("/api/sprava/nastaveni", json={"testovaci_provoz": False})
    assert odpoved.json() == {"testovaci_provoz": False}
    assert k.get("/api/sprava/nastaveni").json() == {"testovaci_provoz": False}
