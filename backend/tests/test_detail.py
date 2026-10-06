"""Detail letu: údaje, historie, zrušení a obnovení, další let odsud, úpravy (modul lety 3.5)."""

from .conftest import _id


def test_detail(conn, osoba, prihlasit, let):
    pilot = osoba("Pilot")
    let_id = let("OK-CRA", {"PIC": pilot}, zpusob="VLASTNI", vzlet="now()")
    k = prihlasit("pilot@example.cz")
    k.post(f"/api/lety/{let_id}/tg")
    d = k.get(f"/api/lety/{let_id}").json()
    assert d["stav"] == "VE_VZDUCHU" and d["rejstrik"] == "OK-CRA" and d["pocet_mist"] == 2
    assert [c["funkce_kod"] for c in d["posadka"]] == ["PIC"]
    assert len(d["tg"]) == 1 and d["misto_vzletu"] == "LKKL"
    assert d["historie"][0]["akce"] == "Založení letu"
    assert k.get("/api/lety/999999").status_code == 404


def test_zrusit_a_obnovit_vlek(conn, osoba, prihlasit, let):
    pilot, vlekar = osoba("Pilot"), osoba("Vlekar")
    vlecna = let("OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": pilot}, zpusob="VLEK", vlecny_let_id=vlecna)
    k = prihlasit("pilot@example.cz")
    pocasi = _id(conn, "lov_duvod_zruseni", "POCASI")
    assert k.post(f"/api/lety/{kluzak}/zrusit", json={"duvod_id": pocasi}).status_code == 200
    vlecny = k.get(f"/api/lety/{vlecna}").json()
    assert vlecny["stav"] == "ZRUSEN" and vlecny["zrusil"] == "Jan Pilot"
    assert k.post(f"/api/lety/{kluzak}/zrusit", json={"duvod_id": pocasi}).status_code == 409
    assert k.post(f"/api/lety/{vlecna}/obnovit").status_code == 200
    assert k.get(f"/api/lety/{kluzak}").json()["stav"] == "NAPLANOVAN"


def test_dalsi_let_odsud(conn, osoba, prihlasit, let):
    pilot, vlekar = osoba("Pilot"), osoba("Vlekar")
    vlecna = let(
        "OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI",
        vzlet="now() - interval '1 hour'", pristani="now() - interval '50 minutes'",
    )  # fmt: skip
    kluzak = let(
        "OK-3819", {"PIC": pilot}, zpusob="VLEK", vlecny_let_id=vlecna,
        vzlet="now() - interval '1 hour'", pristani="now() - interval '10 minutes'",
        misto_pristani="LKLT",
    )  # fmt: skip
    k = prihlasit("pilot@example.cz")
    odpoved = k.post(f"/api/lety/{kluzak}/dalsi")
    assert odpoved.status_code == 200, odpoved.text
    novy = k.get(f"/api/lety/{odpoved.json()['let_id']}").json()
    assert novy["stav"] == "NAPLANOVAN" and novy["misto_vzletu"] == "LKLT"
    assert [c["osoba_id"] for c in novy["posadka"]] == [pilot]
    assert novy["vlek"]["rejstrik"] == "OK-CRA" and novy["vlek"]["pilot"] == "Jan Vlekar"


def test_upravy(conn, osoba, prihlasit, let):
    pilot, jiny = osoba("Pilot"), osoba("Jiny")
    let_id = let(
        "OK-CRA", {"PIC": pilot}, zpusob="VLASTNI",
        vzlet="now() - interval '1 hour'", pristani="now() - interval '10 minutes'",
    )  # fmt: skip
    k = prihlasit("pilot@example.cz")
    verze = k.get(f"/api/lety/{let_id}").json()["verze"]

    d = k.post(
        f"/api/lety/{let_id}",
        json={"verze": verze, "poznamka": "  Přelet  ", "misto_pristani_popis": "pole u Slaného"},
    ).json()
    assert d["poznamka"] == "Přelet" and d["misto_pristani"] == "pole u Slaného"
    assert d["misto_pristani_id"] is None and d["verze"] == verze + 1

    # Stará verze = mezitím změnil někdo jiný.
    stara = k.post(f"/api/lety/{let_id}", json={"verze": verze, "poznamka": "x"})
    assert stara.status_code == 409 and "mezitím změnil" in stara.json()["detail"]

    # Posádka: jiný PIC (i jen změna posádky zvýší verzi); plátce aeroklub.
    pic = _id(conn, "lov_funkce", "PIC")
    d = k.post(
        f"/api/lety/{let_id}",
        json={"verze": d["verze"], "posadka": [{"osoba_id": jiny, "funkce_id": pic}]},
    )
    assert d.status_code == 200, d.text
    d = d.json()
    assert [c["osoba_id"] for c in d["posadka"]] == [jiny] and d["verze"] == verze + 2
    d = k.post(f"/api/lety/{let_id}", json={"verze": d["verze"], "plati_aeroklub": True}).json()
    assert d["plati_aeroklub"] and d["platce_id"] is None

    # Pravidla databáze platí i pro úpravy.
    chyba = k.post(f"/api/lety/{let_id}", json={"verze": d["verze"], "posadka": []})
    assert chyba.status_code == 400 and chyba.json()["detail"] == "musí mít právě jednoho PIC."


def test_zruseny_nejde_upravit(conn, osoba, prihlasit, let):
    pilot = osoba("Pilot")
    let_id = let("OK-2817", {"PIC": pilot}, zrusit=True)
    k = prihlasit("pilot@example.cz")
    verze = k.get(f"/api/lety/{let_id}").json()["verze"]
    odpoved = k.post(f"/api/lety/{let_id}", json={"verze": verze, "poznamka": "x"})
    assert odpoved.status_code == 409
