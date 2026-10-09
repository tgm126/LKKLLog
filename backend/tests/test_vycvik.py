"""Editor výcviku: osnovy, úlohy a typy přezkoušení (docs/modul-osnovy.md, db/042)."""

from .conftest import _id
from .test_akce import _novy


def _osnova(stav: dict, kod: str) -> dict:
    return next(o for o in stav["osnovy"] if o["kod"] == kod)


def _typ(stav: dict, kod: str) -> dict:
    return next(t for t in stav["typy"] if t["kod"] == kod)


def test_pravo(osoba, prihlasit, flotila):
    osoba("Pilot")
    osoba("Vedouci", spravuje_vycvik=True)
    osoba("Admin", admin=True)
    assert prihlasit("pilot@example.cz").get("/api/vycvik").status_code == 403
    vedouci = prihlasit("vedouci@example.cz")
    assert vedouci.get("/api/ja").json()["prava"]["spravuje_vycvik"]
    assert vedouci.get("/api/vycvik").status_code == 200
    # právo přiděluje (i odebírá) jen admin
    vedouci_id = vedouci.get("/api/ja").json()["osoba_id"]
    odpoved = vedouci.post(f"/api/ucty/{vedouci_id}", json={"spravuje_vycvik": False})
    assert odpoved.status_code == 403
    admin = prihlasit("admin@example.cz")
    assert admin.get("/api/ja").json()["prava"]["spravuje_vycvik"]  # admin má vše
    odpoved = admin.post(f"/api/ucty/{vedouci_id}", json={"spravuje_vycvik": False})
    assert odpoved.status_code == 200 and not odpoved.json()["spravuje_vycvik"]


def test_osnovy_a_ulohy(conn, osoba, prihlasit, flotila):
    osoba("Vedouci", spravuje_vycvik=True)
    k = prihlasit("vedouci@example.cz")
    kluzak = _id(conn, "lov_kategorie", "KLUZAK")
    letoun = _id(conn, "lov_kategorie", "LETOUN")
    vycvik, normalni = _id(conn, "lov_ucel", "VYCVIK"), _id(conn, "lov_ucel", "NORMALNI")

    stav = k.post(
        "/api/vycvik/osnovy", json={"kod": " iu ", "nazev": " Výcvik SPL ", "kategorie_id": kluzak}
    ).json()
    iu = _osnova(stav, "IU")
    assert iu["nazev"] == "Výcvik SPL" and iu["ulohy"] == []
    chyba = k.post("/api/vycvik/osnovy", json={"kod": "IU", "nazev": "x", "kategorie_id": kluzak})
    assert chyba.status_code == 400 and chyba.json()["detail"] == "Toto označení už existuje."
    chyba = k.post("/api/vycvik/osnovy", json={"kod": "I U", "nazev": "x", "kategorie_id": kluzak})
    assert chyba.status_code == 400 and chyba.json()["detail"].startswith("Označení: jen velká")

    for kod, nazev in (("4", "Okruhy"), ("8P", "Přezkoušení před sólem")):
        stav = k.post(
            "/api/vycvik/ulohy", json={"osnova_id": iu["id"], "kod": kod, "nazev": nazev}
        ).json()
    ulohy = _osnova(stav, "IU")["ulohy"]
    assert [u["kod"] for u in ulohy] == ["4", "8P"]
    okruhy = ulohy[0]["id"]
    # pořadí ▼
    stav = k.post("/api/vycvik/posun", json={"co": "uloha", "id": okruhy, "smer": 1}).json()
    assert [u["kod"] for u in _osnova(stav, "IU")["ulohy"]] == ["8P", "4"]
    # souhrnné zaškrtnutí osnovy: výcvik všem úlohám; normální jen jedné
    stav = k.post(f"/api/vycvik/osnovy/{iu['id']}/ucel", json={"id": vycvik, "ano": True}).json()
    k.post(f"/api/vycvik/ulohy/{okruhy}/ucel", json={"id": normalni, "ano": True})
    stav = k.get("/api/vycvik").json()
    assert {u["kod"]: u["ucely"] for u in _osnova(stav, "IU")["ulohy"]} == {
        "8P": [vycvik],
        "4": sorted([vycvik, normalni]),
    }

    # úloha použitá v letu: účel nejde odebrat, smazat jen zneplatnit, kategorie osnovy pevná
    pilot = osoba("Pilot")
    let = _novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot}, pob=1, akce="naplanovat",
                uloha_id=okruhy)  # fmt: skip
    assert k.post("/api/lety", json=let).status_code == 200
    chyba = k.post(f"/api/vycvik/ulohy/{okruhy}/ucel", json={"id": normalni, "ano": False})
    assert chyba.status_code == 400
    assert chyba.json()["detail"] == (
        "Úloha IU/4 je s účelem „Normální“ v 1 letech – účel nejde odebrat (úlohu jde zneplatnit)."
    )
    chyba = k.post(f"/api/vycvik/osnovy/{iu['id']}", json={"kategorie_id": letoun})
    assert chyba.json()["detail"] == "Osnova „IU“ má úlohy v letech – kategorii nejde změnit."
    assert k.post(f"/api/vycvik/ulohy/{okruhy}/smazat").status_code == 409
    assert k.post(f"/api/vycvik/osnovy/{iu['id']}/smazat").status_code == 409
    stav = k.post(f"/api/vycvik/ulohy/{okruhy}", json={"platny": False, "nazev": " Okruh "}).json()
    okruh = next(u for u in _osnova(stav, "IU")["ulohy"] if u["id"] == okruhy)
    assert okruh["nazev"] == "Okruh" and not okruh["platny"] and okruh["lety"] == 1

    # nepoužitá úloha jde přesunout do osnovy jiné kategorie i smazat (s účely)
    la = _osnova(
        k.post(
            "/api/vycvik/osnovy", json={"kod": "LA", "nazev": "Letouny", "kategorie_id": letoun}
        ).json(),
        "LA",
    )
    soloid = next(u["id"] for u in _osnova(stav, "IU")["ulohy"] if u["kod"] == "8P")
    stav = k.post(f"/api/vycvik/ulohy/{soloid}", json={"osnova_id": la["id"]}).json()
    assert [u["kod"] for u in _osnova(stav, "LA")["ulohy"]] == ["8P"]
    stav = k.post(f"/api/vycvik/ulohy/{soloid}/smazat").json()
    assert _osnova(stav, "LA")["ulohy"] == []
    assert "LA" not in [
        o["kod"] for o in k.post(f"/api/vycvik/osnovy/{la['id']}/smazat").json()["osnovy"]
    ]

    # audit: úpravy osnov a úloh v historii, pořadí ne
    akce = [r["akce"] for r in conn.execute(
        """SELECT akce FROM lkkl.v_audit
           WHERE tabulka = 'lov_osnova' OR tabulka LIKE 'lov_uloha%' ORDER BY id"""
    ).fetchall()]  # fmt: skip
    assert akce[:3] == ["Založení osnovy", "Založení úlohy", "Založení úlohy"]
    assert "Úloha: přidání účelu" in akce and "Smazání úlohy" in akce
    assert akce.count("Úprava úlohy") == 2  # zneplatnění + přesun, pořadí se nepíše


def test_typy_prezkouseni(conn, osoba, prihlasit, flotila):
    osoba("Vedouci", spravuje_vycvik=True)
    k = prihlasit("vedouci@example.cz")
    kluzak = _id(conn, "lov_kategorie", "KLUZAK")
    letoun = _id(conn, "lov_kategorie", "LETOUN")
    fe_s = conn.execute(
        """INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi)
           VALUES ('FE_S', 'FE(S)', 20) RETURNING id"""
    ).fetchone()["id"]
    conn.execute("INSERT INTO lkkl.lov_opravneni_kategorie VALUES (%s, %s)", (fe_s, kluzak))

    stav = k.post(
        "/api/vycvik/typy",
        json={"kod": "pc-spl", "nazev": "Přezkoušení SPL", "kategorie_id": kluzak},
    ).json()
    typ = _typ(stav, "PC-SPL")
    assert typ["opravneni"] == [] and typ["lety"] == 0
    stav = k.post(f"/api/vycvik/typy/{typ['id']}/opravneni", json={"id": fe_s, "ano": True}).json()
    assert _typ(stav, "PC-SPL")["opravneni"] == [fe_s]
    assert next(o for o in stav["opravneni"] if o["id"] == fe_s)["kategorie"] == [kluzak]
    # examinátor v náhledu: osoba s FE(S) pro kluzák
    examinator = osoba("Examinator", ucet=False)
    conn.execute(
        "INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id) VALUES (%s, %s)",
        (examinator, fe_s),
    )
    conn.execute(
        "INSERT INTO lkkl.lov_osoba_opravneni_kategorie VALUES (%s, %s, %s)",
        (examinator, fe_s, kluzak),
    )
    stav = k.get("/api/vycvik").json()
    assert [(e["prijmeni"], e["prezkouseni"]) for e in stav["examinatori"]] == [
        ("Examinator", [typ["id"]])
    ]

    # oprávnění jen pro kategorii typu (databáze)
    stav = k.post(
        "/api/vycvik/typy", json={"kod": "PC-SEP", "nazev": "SEP", "kategorie_id": letoun}
    ).json()
    sep = _typ(stav, "PC-SEP")
    chyba = k.post(f"/api/vycvik/typy/{sep['id']}/opravneni", json={"id": fe_s, "ano": True})
    assert chyba.status_code == 400
    assert chyba.json()["detail"] == "Oprávnění „FE(S)“ se pro kategorii typu přezkoušení nevydává."
    # změna kategorie nepoužitého typu: oprávnění, které se pro ni nevydává, odpadne
    stav = k.post(f"/api/vycvik/typy/{typ['id']}", json={"kategorie_id": letoun}).json()
    assert (
        _typ(stav, "PC-SPL")["opravneni"] == [] and _typ(stav, "PC-SPL")["kategorie_id"] == letoun
    )
    k.post(f"/api/vycvik/typy/{typ['id']}", json={"kategorie_id": kluzak})

    # použitý typ: kategorii ani smazání ne, zneplatnit ano
    pilot, zkouseny = osoba("Pilot"), osoba("Zkouseny")
    let = _novy(
        conn, rejstrik="OK-2817", ucel="PREZKOUSENI", akce="naplanovat",
        posadka={"PIC": pilot, "PREZKOUSENY": zkouseny}, prezkouseni_id=typ["id"],
    )  # fmt: skip
    assert k.post("/api/lety", json=let).status_code == 200
    chyba = k.post(f"/api/vycvik/typy/{typ['id']}", json={"kategorie_id": letoun})
    assert chyba.json()["detail"] == "Typ je použit v letech – kategorii nejde změnit."
    assert k.post(f"/api/vycvik/typy/{typ['id']}/smazat").status_code == 409
    stav = k.post(f"/api/vycvik/typy/{typ['id']}", json={"platny": False}).json()
    assert not _typ(stav, "PC-SPL")["platny"] and _typ(stav, "PC-SPL")["lety"] == 1
    assert "PC-SEP" not in [
        t["kod"] for t in k.post(f"/api/vycvik/typy/{sep['id']}/smazat").json()["typy"]
    ]
    akce = {
        r["akce"]
        for r in conn.execute(
            "SELECT akce FROM lkkl.v_audit WHERE tabulka LIKE 'lov_prezkouseni%'"
        ).fetchall()
    }
    assert {
        "Založení typu přezkoušení",
        "Přezkoušení: přidání oprávnění",
        "Smazání typu přezkoušení",
    } <= akce
