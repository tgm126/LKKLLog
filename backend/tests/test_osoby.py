"""Správa osob a práva k ní (docs/modul-osoby.md)."""


def test_prava_k_osobam(osoba, prihlasit):
    """Seznam osob jen pro správce osob a admina; práva přiděluje jen admin."""
    osoba("Admin", admin=True)
    osoba("Spravce", spravuje_osoby=True)
    pilot = osoba("Pilot")
    assert prihlasit("pilot@example.cz").get("/api/osoby").status_code == 403

    spravce = prihlasit("spravce@example.cz")
    assert spravce.get("/api/ja").json()["prava"] == {
        "admin": False,
        "smi_odblokovat": False,
        "spravuje_osoby": True,
        "spravuje_letadla": False,
        "spravuje_vycvik": False,
    }
    assert spravce.get("/api/osoby").status_code == 200
    # Správce smí zablokovat účet, ale ne přidělit (ani odebrat) právo.
    assert (
        spravce.post(f"/api/ucty/{pilot}", json={"prihlaseni_povoleno": False}).status_code == 200
    )
    odpoved = spravce.post(f"/api/ucty/{pilot}", json={"spravuje_osoby": True})
    assert odpoved.status_code == 403

    admin = prihlasit("admin@example.cz")
    odpoved = admin.post(
        f"/api/ucty/{pilot}", json={"spravuje_osoby": True, "prihlaseni_povoleno": True}
    )
    assert odpoved.status_code == 200 and odpoved.json()["spravuje_osoby"]


def test_spravce_nesmi_na_admina_ani_sam_sebe(osoba, prihlasit):
    admin = osoba("Admin", admin=True)
    spravce = osoba("Spravce", spravuje_osoby=True)
    k = prihlasit("spravce@example.cz")
    assert k.post(f"/api/ucty/{admin}", json={"prihlaseni_povoleno": False}).status_code == 403
    assert k.post(f"/api/osoby/{admin}", json={"platny": False}).status_code == 403
    odpoved = k.post(f"/api/osoby/{spravce}", json={"platny": False})
    assert odpoved.status_code == 400 and "Sám sebe" in odpoved.json()["detail"]


def test_nova_osoba_upravy_a_chyby(osoba, prihlasit):
    osoba("Spravce", spravuje_osoby=True)
    k = prihlasit("spravce@example.cz")
    nova = k.post(
        "/api/osoby",
        json={
            "jmeno": " Eva ",
            "prijmeni": "Malá",
            "telefon": "602 123 456",
            "cislo_clena": "1042",
        },
    )
    assert nova.status_code == 200, nova.text
    o = nova.json()
    assert (o["jmeno"], o["telefon"], o["clen"], o["ucet"]) == ("Eva", "+420602123456", True, None)

    # Mění se jen poslané údaje; prázdný text maže.
    upravena = k.post(
        f"/api/osoby/{o['id']}", json={"telefon": "00421 905 111 222", "cislo_clena": ""}
    )
    assert upravena.json()["telefon"] == "+421905111222"
    assert upravena.json()["cislo_clena"] is None and upravena.json()["prijmeni"] == "Malá"

    # Chyby z databáze čitelně.
    chyby = {
        "email": ("neni-email", "Neplatný e-mail."),
        "telefon": ("12", "Telefon zadejte s předvolbou, např. +420 602 123 456."),
        "prijmeni": ("  ", "Příjmení musí být vyplněné."),
    }
    for pole, (hodnota, hlaska) in chyby.items():
        odpoved = k.post(f"/api/osoby/{o['id']}", json={pole: hodnota})
        assert odpoved.status_code == 400 and odpoved.json()["detail"] == hlaska, pole
    odpoved = k.post(f"/api/osoby/{o['id']}", json={"email": "SPRAVCE@example.cz"})
    assert odpoved.json()["detail"] == "Tento e-mail už má jiná osoba."
    odpoved = k.post(f"/api/osoby/{o['id']}", json={"clen": False, "cislo_clena": "7"})
    assert odpoved.json()["detail"] == "Číslo člena má jen člen klubu."


def test_opravneni_a_historie(conn, osoba, prihlasit, flotila):
    """Oprávnění po kategoriích letadel (db/024): první kategorie oprávnění přidá, poslední
    odebere; jen povolené kategorie; omezení u oprávnění osoby."""
    osoba("Spravce", spravuje_osoby=True)
    pilot = osoba("Pilot", ucet=False)
    k = prihlasit("spravce@example.cz")
    kat = {r["kod"]: r["id"] for r in conn.execute("SELECT kod, id FROM lkkl.lov_kategorie")}
    vlekar = conn.execute("SELECT id FROM lkkl.lov_opravneni WHERE kod = 'VLEKAR'").fetchone()["id"]
    fi = conn.execute(
        """INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi)
           VALUES ('FI_S', 'FI(S)', 10) RETURNING id"""
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO lkkl.lov_opravneni_kategorie VALUES (%s, %s), (%s, %s)",
        (vlekar, kat["LETOUN"], fi, kat["KLUZAK"]),
    )
    conn.execute(
        """INSERT INTO lkkl.lov_opravneni_role
           SELECT %s, id FROM lkkl.lov_role WHERE kod IN ('INSTRUKTOR', 'DOZOR')""",
        (fi,),
    )

    seznam = {o["id"]: o for o in k.get("/api/osoby").json()["opravneni"]}
    assert seznam[vlekar] == {
        "id": vlekar,
        "nazev": "Vlekař",
        "lze_omezit": False,
        "kategorie": [{"id": kat["LETOUN"], "nazev": "Letoun"}],
    }
    assert seznam[fi]["lze_omezit"]

    def zmenit(opravneni, kategorie, ma):
        return k.post(
            f"/api/osoby/{pilot}/opravneni",
            json={"opravneni_id": opravneni, "kategorie_id": kat[kategorie], "ma": ma},
        )

    o = zmenit(vlekar, "LETOUN", True).json()
    assert o["opravneni"] == [{"id": vlekar, "omezene": False, "kategorie": [kat["LETOUN"]]}]
    odpoved = zmenit(vlekar, "KLUZAK", True)
    assert odpoved.status_code == 400
    assert odpoved.json()["detail"] == "Toto oprávnění se pro tuto kategorii nevydává."
    k.post(f"/api/osoby/{pilot}", json={"telefon": "+420602000111"})
    o = zmenit(vlekar, "LETOUN", False).json()
    assert o["opravneni"] == []  # s poslední kategorií zmizí i oprávnění

    # Omezení: jen u oprávnění, které osoba má.
    omezit = {"opravneni_id": fi, "omezene": True}
    assert k.post(f"/api/osoby/{pilot}/omezeni", json=omezit).status_code == 404
    zmenit(fi, "KLUZAK", True)
    o = k.post(f"/api/osoby/{pilot}/omezeni", json=omezit).json()
    assert o["opravneni"] == [{"id": fi, "omezene": True, "kategorie": [kat["KLUZAK"]]}]

    akce = [z["akce"] for z in o["historie"]]
    assert akce == [
        "Omezení oprávnění",
        "Oprávnění: přidání kategorie",
        "Přidání oprávnění",
        "Odebrání oprávnění",
        "Oprávnění: odebrání kategorie",
        "Úprava osoby",
        "Oprávnění: přidání kategorie",
        "Přidání oprávnění",
        "Založení osoby",
    ]
    assert o["historie"][0]["kdo"] == "Jan Spravce"
    assert o["historie"][1]["popis"] == "oprávnění FI(S), kategorie Kluzák"
