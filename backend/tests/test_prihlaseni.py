"""Přihlášení, relace, odhlášení, ochrana proti hádání hesla a CSRF."""

from app.prihlasovani import CHYBA_PRIHLASENI, COOKIE

from .conftest import HESLO


def test_prihlaseni_a_ja(klient, osoba, conn):
    osoba_id = osoba("Novak", admin=True)
    k = klient()
    odpoved = k.post("/api/prihlaseni", json={"email": "NOVAK@example.cz ", "heslo": HESLO})
    assert odpoved.status_code == 200
    assert "httponly" in odpoved.headers["set-cookie"].lower()
    assert "secure" in odpoved.headers["set-cookie"].lower()
    ja = k.get("/api/ja").json()
    assert ja["osoba_id"] == osoba_id and ja["prava"] == {"admin": True, "smi_odblokovat": False}
    assert ja["puvodni"] is None
    radek = conn.execute(
        "SELECT posledni_prihlaseni FROM lkkl.ucet WHERE osoba_id = %s", (osoba_id,)
    ).fetchone()
    assert radek["posledni_prihlaseni"] is not None
    # V databázi je jen otisk klíče, ne klíč z cookie.
    klic = k.cookies[COOKIE]
    assert not conn.execute("SELECT 1 FROM lkkl.relace WHERE id = %s", (klic,)).fetchone()


def test_chybne_prihlaseni_neprozradi_ucet(klient, osoba, conn):
    osoba("Novak")
    osoba("Bezhesla", heslo=None)
    osoba("Bezuctu", ucet=False)
    neaktivni = osoba("Neaktivni")
    conn.execute("UPDATE lkkl.lov_osoba SET aktivni = false WHERE id = %s", (neaktivni,))
    k = klient()
    for email, heslo in [
        ("novak@example.cz", "spatne-heslo-1"),
        ("nikdo@example.cz", HESLO),
        ("bezhesla@example.cz", HESLO),
        ("bezuctu@example.cz", HESLO),
        ("neaktivni@example.cz", HESLO),
    ]:
        odpoved = k.post("/api/prihlaseni", json={"email": email, "heslo": heslo})
        assert odpoved.status_code == 401, email
        assert odpoved.json()["detail"] == CHYBA_PRIHLASENI
    assert k.get("/api/ja").status_code == 401


def test_zablokovani_po_peti_pokusech_a_odblokovani(klient, osoba, prihlasit, conn):
    osoba("Novak")
    osoba("Spravce", smi_odblokovat=True)
    zarizeni = prihlasit("novak@example.cz")  # už přihlášené zařízení
    k = klient()
    for _ in range(4):
        assert (
            k.post(
                "/api/prihlaseni", json={"email": "novak@example.cz", "heslo": "x" * 10}
            ).status_code
            == 401
        )
    odpoved = k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": "x" * 10})
    assert odpoved.status_code == 429 and "15 min" in odpoved.json()["detail"]
    # Ani správné heslo teď nepustí, ale přihlášené zařízení funguje dál.
    assert (
        k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": HESLO}).status_code
        == 429
    )
    assert zarizeni.get("/api/ja").status_code == 200

    spravce = prihlasit("spravce@example.cz")
    [zablokovany] = spravce.get("/api/ucty/zablokovane").json()
    assert zablokovany["prijmeni"] == "Novak"
    assert zarizeni.get("/api/ucty/zablokovane").status_code == 403
    assert spravce.post(f"/api/ucty/{zablokovany['osoba_id']}/odblokovat").status_code == 204
    assert (
        k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": HESLO}).status_code
        == 200
    )


def test_uspesne_prihlaseni_vynuluje_pokusy(klient, osoba, conn):
    osoba_id = osoba("Novak")
    k = klient()
    for _ in range(4):
        k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": "x" * 10})
    k.post("/api/prihlaseni", json={"email": "novak@example.cz", "heslo": HESLO})
    pokusy = conn.execute(
        "SELECT neuspesne_pokusy FROM lkkl.ucet WHERE osoba_id = %s", (osoba_id,)
    ).fetchone()["neuspesne_pokusy"]
    assert pokusy == 0


def test_odhlaseni(osoba, prihlasit):
    osoba("Novak")
    k = prihlasit("novak@example.cz")
    assert k.post("/api/odhlaseni").status_code == 204
    assert k.get("/api/ja").status_code == 401


def test_prosla_relace_se_smaze(osoba, prihlasit, conn):
    osoba_id = osoba("Novak")
    k = prihlasit("novak@example.cz")
    conn.execute(
        """UPDATE lkkl.relace SET vytvorena = now() - interval '31 days',
           plati_do = now() - interval '1 day' WHERE osoba_id = %s""",
        (osoba_id,),
    )
    assert k.get("/api/ja").status_code == 401
    assert not conn.execute("SELECT 1 FROM lkkl.relace WHERE osoba_id = %s", (osoba_id,)).fetchone()


def test_relace_se_prodluzuje_nejvys_jednou_za_hodinu(osoba, prihlasit, conn):
    osoba_id = osoba("Novak")
    k = prihlasit("novak@example.cz")
    conn.execute(
        """UPDATE lkkl.relace SET posledni_aktivita = now() - interval '2 hours',
           plati_do = now() + interval '1 day' WHERE osoba_id = %s""",
        (osoba_id,),
    )
    odpoved = k.get("/api/ja")
    assert odpoved.status_code == 200 and COOKIE in odpoved.headers["set-cookie"]
    zbyva = conn.execute(
        "SELECT plati_do - now() AS zbyva FROM lkkl.relace WHERE osoba_id = %s", (osoba_id,)
    ).fetchone()["zbyva"]
    assert zbyva.days >= 29
    # Hned další požadavek už nic nezapisuje.
    assert "set-cookie" not in k.get("/api/ja").headers


def test_zablokovani_uctu_nebo_osoby_ukonci_relaci(osoba, prihlasit, conn):
    osoba_id = osoba("Novak")
    k = prihlasit("novak@example.cz")
    conn.execute("UPDATE lkkl.lov_osoba SET aktivni = false WHERE id = %s", (osoba_id,))
    assert k.get("/api/ja").status_code == 401


def test_csrf_vyzaduje_povoleny_puvod(klient, osoba):
    osoba("Novak")
    for origin in (None, "https://zly.example"):
        odpoved = klient(origin).post(
            "/api/prihlaseni", json={"email": "novak@example.cz", "heslo": HESLO}
        )
        assert odpoved.status_code == 403
    assert klient(None).get("/api/ja").status_code == 401  # čtení bez Origin projde ke kontrole


def test_zarizeni_a_odhlaseni_ostatnich(osoba, prihlasit):
    osoba("Novak")
    telefon = prihlasit("novak@example.cz")
    pocitac = prihlasit("novak@example.cz")
    zarizeni = pocitac.get("/api/zarizeni").json()
    assert len(zarizeni) == 2 and sum(z["aktualni"] for z in zarizeni) == 1
    assert pocitac.post("/api/zarizeni/odhlasit-ostatni").status_code == 204
    assert telefon.get("/api/ja").status_code == 401
    assert pocitac.get("/api/ja").status_code == 200
