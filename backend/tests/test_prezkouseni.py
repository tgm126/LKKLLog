"""Typy přezkoušení: u letu s účelem Přezkoušení místo úlohy, nabídka examinátora podle typu
(docs/modul-prezkouseni.md, db/041)."""

from .conftest import _id
from .test_akce import _novy


def _typ(conn, kod: str, nazev: str, kategorie: str) -> int:
    return conn.execute(
        """INSERT INTO lkkl.lov_prezkouseni (kod, nazev, poradi, kategorie_id)
           SELECT %s, %s, 10, id FROM lkkl.lov_kategorie WHERE kod = %s RETURNING id""",
        (kod, nazev, kategorie),
    ).fetchone()["id"]


def test_typ_prezkouseni_u_letu(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    zkouseny = osoba("Zkouseny")
    data = _novy(
        conn, rejstrik="OK-2817", ucel="PREZKOUSENI",
        posadka={"PIC": pilot_id, "PREZKOUSENY": zkouseny}, akce="naplanovat",
    )  # fmt: skip
    # Pro kluzáky zatím žádný typ není – přezkoušení jde zapsat i bez něj.
    assert k.post("/api/lety", json=data).status_code == 200

    pc_spl = _typ(conn, "PC-SPL", "Přezkoušení odborné způsobilosti SPL", "KLUZAK")
    pc_sep = _typ(conn, "PC-SEP", "Přezkoušení SEP", "LETOUN")
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 400
    assert odpoved.json()["detail"] == "U přezkoušení je typ přezkoušení povinný."
    odpoved = k.post("/api/lety", json={**data, "prezkouseni_id": pc_sep})
    assert odpoved.json()["detail"] == "Typ přezkoušení patří k jiné kategorii letadla."
    normalni = _novy(
        conn, rejstrik="OK-3819", posadka={"PIC": pilot_id}, pob=1, akce="naplanovat",
        prezkouseni_id=pc_spl,
    )  # fmt: skip
    odpoved = k.post("/api/lety", json=normalni)
    assert odpoved.json()["detail"] == "Typ přezkoušení jde jen u účelu Přezkoušení."

    odpoved = k.post("/api/lety", json={**data, "prezkouseni_id": pc_spl})
    assert odpoved.status_code == 200, odpoved.text
    let_id = odpoved.json()["let_id"]
    pasek = next(p for p in k.get("/api/lety").json()["lety"] if p["id"] == let_id)
    assert (pasek["prezkouseni_kod"], pasek["prezkouseni"]) == (
        "PC-SPL",
        "PC-SPL Přezkoušení odborné způsobilosti SPL",
    )
    assert pasek["uloha"] is None and pasek["pob"] == 2
    detail = k.get(f"/api/lety/{let_id}").json()
    assert detail["prezkouseni_id"] == pc_spl and detail["platce_id"] == zkouseny

    # Úprava v detailu: jiný typ téže kategorie; historie ho ukáže čitelně.
    pc_cloud = _typ(conn, "PC-CLOUD", "Přezkoušení pro lety v oblacích", "KLUZAK")
    odpoved = k.post(
        f"/api/lety/{let_id}", json={"verze": detail["verze"], "prezkouseni_id": pc_cloud}
    )
    assert odpoved.status_code == 200, odpoved.text
    zmena = odpoved.json()["historie"][-1]
    assert "PC-SPL Přezkoušení odborné způsobilosti SPL" in zmena["popis"]
    assert "PC-CLOUD Přezkoušení pro lety v oblacích" in zmena["popis"]

    # Neplatný typ se nenabízí a nejde nově použít.
    conn.execute("UPDATE lkkl.lov_prezkouseni SET platny = false WHERE id = %s", (pc_spl,))
    nabidka = {p["kod"] for p in k.get("/api/lety/nabidky").json()["prezkouseni"]}
    assert nabidka == {"PC-CLOUD", "PC-SEP"}
    odpoved = k.post("/api/lety", json={**data, "prezkouseni_id": pc_spl})
    assert odpoved.json()["detail"].endswith("už neplatí – nejde použít.")


def test_nabidka_examinatora(conn, pilot, osoba, flotila):
    """Examinátor se nabízí podle typu přezkoušení: oprávnění z vazby a kategorie typu."""
    pilot_id, k = pilot
    jen_letoun = osoba("Letoun", ucet=False)
    nikdo = osoba("Nikdo", ucet=False)
    pc_spl = _typ(conn, "PC-SPL", "Přezkoušení SPL", "KLUZAK")
    st_spl = _typ(conn, "ST-SPL", "Zkouška dovednosti SPL", "KLUZAK")
    fe_s = conn.execute(
        """INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi)
           VALUES ('FE_S', 'FE(S)', 20) RETURNING id"""
    ).fetchone()["id"]
    conn.execute(
        """INSERT INTO lkkl.lov_opravneni_kategorie
           SELECT %s, id FROM lkkl.lov_kategorie WHERE kod IN ('KLUZAK', 'LETOUN')""",
        (fe_s,),
    )
    conn.execute(
        "INSERT INTO lkkl.lov_prezkouseni_opravneni VALUES (%s, %s), (%s, %s)",
        (pc_spl, fe_s, st_spl, fe_s),
    )
    conn.execute(
        "INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id) VALUES (%s, %s), (%s, %s)",
        (pilot_id, fe_s, jen_letoun, fe_s),
    )
    conn.execute(
        """INSERT INTO lkkl.lov_osoba_opravneni_kategorie (osoba_id, opravneni_id, kategorie_id)
           VALUES (%s, %s, %s), (%s, %s, %s)""",
        (pilot_id, fe_s, _id(conn, "lov_kategorie", "KLUZAK"),
         jen_letoun, fe_s, _id(conn, "lov_kategorie", "LETOUN")),
    )  # fmt: skip
    nabidky = k.get("/api/lety/nabidky").json()
    osoby = {o["id"]: o for o in nabidky["osoby"]}
    assert sorted(osoby[pilot_id]["prezkouseni"]) == sorted([pc_spl, st_spl])
    assert osoby[jen_letoun]["prezkouseni"] == []  # FE(S) má jen pro letouny
    assert osoby[nikdo]["prezkouseni"] == []
    # role examinátora (účel + funkce) už není – rozhoduje typ přezkoušení
    assert osoby[pilot_id]["role"] == []
    assert {p["kod"]: p["kategorie_kod"] for p in nabidky["prezkouseni"]} == {
        "PC-SPL": "KLUZAK",
        "ST-SPL": "KLUZAK",
    }
