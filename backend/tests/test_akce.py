"""Akce letu (vzlet, přistání, T&G, Zpět) a nový let z průvodce (docs/modul-lety.md)."""

import re

from .conftest import _id


def _stav(conn, let_id: int) -> dict:
    return conn.execute(
        """SELECT stav, cas_vzletu, cas_pristani, misto_pristani, pocet_pristani, pob,
                  platce_id, plati_aeroklub, vlecny_let_id
           FROM lkkl.v_let WHERE id = %s""",
        (let_id,),
    ).fetchone()


def test_vzlet_jen_jednou_a_zpet(conn, pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-2817", {"PIC": pilot_id})
    odpoved = k.post(f"/api/lety/{let_id}/vzlet")
    assert odpoved.status_code == 200 and odpoved.json()["rejstrik"] == "OK-2817"
    assert _stav(conn, let_id)["stav"] == "VE_VZDUCHU"

    znovu = k.post(f"/api/lety/{let_id}/vzlet")
    assert znovu.status_code == 409 and znovu.json()["detail"].startswith("OK-2817: Už vzlétl v")

    assert k.post(f"/api/lety/{let_id}/zpet", json={"akce": "vzlet"}).status_code == 200
    assert _stav(conn, let_id)["stav"] == "NAPLANOVAN"


def test_vzlet_vleku_pro_oba(conn, pilot, osoba, let):
    pilot_id, k = pilot
    vlekar = osoba("Vlekar")
    vlecna = let("OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": pilot_id}, zpusob="VLEK", vlecny_let_id=vlecna)
    assert k.post(f"/api/lety/{vlecna}/vzlet").status_code == 200  # stisk u kterékoli z dvojice
    assert _stav(conn, kluzak)["cas_vzletu"] == _stav(conn, vlecna)["cas_vzletu"] is not None
    assert k.post(f"/api/lety/{kluzak}/zpet", json={"akce": "vzlet"}).status_code == 200
    assert _stav(conn, vlecna)["stav"] == _stav(conn, kluzak)["stav"] == "NAPLANOVAN"


def test_tg_pristani_a_zpet(conn, pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-CRA", {"PIC": pilot_id}, zpusob="VLASTNI", vzlet="now()")
    # (V transakci testu má každé T&G stejný čas – proto jen jedno; Zpět ho vrátí.)
    assert k.post(f"/api/lety/{let_id}/tg").status_code == 200
    assert k.post(f"/api/lety/{let_id}/zpet", json={"akce": "tg"}).status_code == 200
    assert k.post(f"/api/lety/{let_id}/tg").status_code == 200
    odpoved = k.post(f"/api/lety/{let_id}/pristani")
    assert odpoved.status_code == 200
    stav = _stav(conn, let_id)
    assert stav["stav"] == "UKONCEN" and stav["misto_pristani"] == "LKKL"
    assert stav["pocet_pristani"] == 2  # T&G + přistání

    znovu = k.post(f"/api/lety/{let_id}/pristani")
    assert znovu.status_code == 409 and "Už přistál" in znovu.json()["detail"]
    assert k.post(f"/api/lety/{let_id}/zpet", json={"akce": "pristani"}).status_code == 200
    stav = _stav(conn, let_id)  # místo přistání zůstane jako plán
    assert stav["stav"] == "VE_VZDUCHU" and stav["misto_pristani"] == "LKKL"


def test_misto_pristani_predem(conn, pilot, let):
    """Místo přistání je od založení (plán); přistání ho zachová, jde upravit i ve vzduchu
    (db/027)."""
    pilot_id, k = pilot
    let_id = let("OK-CRA", {"PIC": pilot_id}, zpusob="VLASTNI", misto_pristani="LKLT")
    assert _stav(conn, let_id)["misto_pristani"] == "LKLT"
    assert k.post(f"/api/lety/{let_id}/vzlet").status_code == 200
    verze = k.get(f"/api/lety/{let_id}").json()["verze"]
    upraveny = k.post(
        f"/api/lety/{let_id}", json={"verze": verze, "misto_pristani_popis": "pole u Slaného"}
    )
    assert upraveny.status_code == 200 and upraveny.json()["misto_pristani"] == "pole u Slaného"
    assert k.post(f"/api/lety/{let_id}/pristani").status_code == 200
    assert _stav(conn, let_id)["misto_pristani"] == "pole u Slaného"


def test_tg_jen_motorove(pilot, let):
    pilot_id, k = pilot
    kluzak = let("OK-2817", {"PIC": pilot_id}, vzlet="now()")
    assert k.post(f"/api/lety/{kluzak}/tg").status_code == 409


def test_zpet_jen_hned(pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '2 minutes'")
    odpoved = k.post(f"/api/lety/{let_id}/zpet", json={"akce": "vzlet"})
    assert odpoved.status_code == 409 and odpoved.json()["detail"] == "OK-2817: vrátit už nejde."


def test_prekryv(pilot, let):
    """Letadlo, které už letí, nevzlétne znovu – hláška s údaji druhého letu (db/025)."""
    pilot_id, k = pilot
    let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '10 minutes'")
    druhy = let("OK-2817", {"PIC": pilot_id})
    odpoved = k.post(f"/api/lety/{druhy}/vzlet")
    assert odpoved.status_code == 400
    assert re.fullmatch(
        r"OK-2817 už letí \(vzlet \d\d:\d\d UTC, PIC Jan Pilot\)\.", odpoved.json()["detail"]
    )


# --- nový let z průvodce --------------------------------------------------------------------


def _novy(conn, **udaje) -> dict:
    """Tělo požadavku POST /api/lety; letadlo, účel a způsob podle kódu."""
    letadlo = conn.execute(
        "SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = %s", (udaje.pop("rejstrik"),)
    ).fetchone()["id"]
    return {
        "letadlo_id": letadlo,
        "ucel_id": _id(conn, "lov_ucel", udaje.pop("ucel", "NORMALNI")),
        "zpusob_vzletu_id": _id(conn, "lov_zpusob_vzletu", udaje.pop("zpusob", "NAVIJAK")),
        "posadka": [
            {"osoba_id": o, "funkce_id": _id(conn, "lov_funkce", f)}
            for f, o in udaje.pop("posadka").items()
        ],
        **udaje,
    }


def test_novy_let_vzlet_ted(conn, pilot, flotila):
    pilot_id, k = pilot
    data = _novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, pob=1, akce="vzlet")
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 200, odpoved.text
    stav = _stav(conn, odpoved.json()["let_id"])
    assert stav["stav"] == "VE_VZDUCHU" and stav["platce_id"] == pilot_id  # plátce = PIC


def test_novy_let_vycvik(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    zak = osoba("Zak")
    data = _novy(
        conn, rejstrik="OK-2817", ucel="VYCVIK", posadka={"PIC": pilot_id, "ZAK": zak},
        akce="naplanovat",
    )  # fmt: skip
    # Pro kluzáky zatím žádná osnova není – úloha se nevyžaduje (let jde zapsat).
    assert k.post("/api/lety", json=data).status_code == 200

    osnova = conn.execute(
        """INSERT INTO lkkl.lov_osnova (kod, nazev, poradi, kategorie_id)
           SELECT 'ZAKLAD', 'Základní', 10, id FROM lkkl.lov_kategorie WHERE kod = 'KLUZAK'
           RETURNING id"""
    ).fetchone()["id"]
    uloha = conn.execute(
        """INSERT INTO lkkl.lov_uloha (kod, nazev, poradi, osnova_id)
           VALUES ('B3', 'B3 – Okruhy', 10, %s) RETURNING id""",
        (osnova,),
    ).fetchone()["id"]
    conn.execute(
        "INSERT INTO lkkl.lov_uloha_ucel (uloha_id, ucel_id) VALUES (%s, %s)",
        (uloha, _id(conn, "lov_ucel", "VYCVIK")),
    )
    # Teď úloha pro výcvik na kluzáku existuje – bez ní to databáze odmítne (bez „Let 12:“).
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 400
    assert odpoved.json()["detail"] == "u tohoto účelu je úloha povinná."
    # Úloha jiného účelu nebo pro jinou kategorii neprojde.
    solo_let = _novy(
        conn, rejstrik="OK-2817", ucel="VYCVIK_SOLO", posadka={"PIC": zak, "DOZOR": pilot_id},
        akce="naplanovat", uloha_id=uloha,
    )  # fmt: skip
    odpoved = k.post("/api/lety", json=solo_let)
    assert odpoved.json()["detail"] == "úloha nepatří k účelu letu nebo ke kategorii letadla."
    # Na letounu (kategorie bez osnovy) výcvik bez úlohy jde.
    letoun = _novy(
        conn, rejstrik="OK-CRA", ucel="VYCVIK", zpusob="VLASTNI",
        posadka={"PIC": pilot_id, "ZAK": zak}, akce="naplanovat",
    )  # fmt: skip
    assert k.post("/api/lety", json=letoun).status_code == 200

    odpoved = k.post("/api/lety", json={**data, "uloha_id": uloha})
    assert odpoved.status_code == 200, odpoved.text
    stav = _stav(conn, odpoved.json()["let_id"])
    assert stav["stav"] == "NAPLANOVAN" and stav["platce_id"] == zak  # u výcviku platí žák
    assert stav["pob"] == 2  # z posádky


def test_novy_probehly_aerovlek(conn, pilot, osoba, flotila):
    pilot_id, k = pilot
    vlekar = osoba("Vlekar")
    casy = conn.execute(
        """SELECT now() - interval '50 minutes' AS vzlet, now() - interval '10 minutes' AS pristani,
                  now() - interval '40 minutes' AS vlecna"""
    ).fetchone()
    data = _novy(
        conn,
        rejstrik="OK-3819",
        zpusob="VLEK",
        posadka={"PIC": pilot_id},
        pob=1,
        vlecna_id=conn.execute(
            "SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = 'OK-CRA'"
        ).fetchone()["id"],
        vlekar_id=vlekar,
        plati_aeroklub=True,
        akce="probehly",
        cas_vzletu=casy["vzlet"].isoformat(),
        cas_pristani=casy["pristani"].isoformat(),
        cas_pristani_vlecne=casy["vlecna"].isoformat(),
    )
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 200, odpoved.text
    kluzak = _stav(conn, odpoved.json()["let_id"])
    vlecna = _stav(conn, kluzak["vlecny_let_id"])
    assert kluzak["stav"] == vlecna["stav"] == "UKONCEN"
    assert kluzak["cas_vzletu"] == vlecna["cas_vzletu"] == casy["vzlet"]
    assert vlecna["cas_pristani"] == casy["vlecna"] and vlecna["pob"] == 1
    assert kluzak["plati_aeroklub"] and vlecna["plati_aeroklub"]
    # nezadané místo přistání = moje letiště pro oba lety vleku
    assert kluzak["misto_pristani"] == vlecna["misto_pristani"] == "LKKL"

    # Přelet vleku: zadané místo přistání platí pro kluzák i vlečnou.
    letnany = conn.execute("SELECT id FROM lkkl.lov_letiste WHERE kod = 'LKLT'").fetchone()["id"]
    prelet = k.post("/api/lety", json={**data, "akce": "naplanovat", "misto_pristani_id": letnany})
    assert prelet.status_code == 200, prelet.text
    kluzak = _stav(conn, prelet.json()["let_id"])
    vlecna = _stav(conn, kluzak["vlecny_let_id"])
    assert kluzak["misto_pristani"] == vlecna["misto_pristani"] == "LKLT"

    # Vlekař nemůže pilotovat i kluzák.
    assert k.post("/api/lety", json={**data, "vlekar_id": pilot_id}).status_code == 400
    # Bez času přistání vlečné proběhlý aerovlek nejde.
    bez = {**data, "cas_pristani_vlecne": None}
    assert k.post("/api/lety", json=bez).status_code == 400


def test_nabidky(conn, pilot, let):
    pilot_id, k = pilot
    let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '5 minutes'")
    nabidky = k.get("/api/lety/nabidky").json()
    letadla = {a["rejstrik"]: a for a in nabidky["letadla"]}
    assert letadla["OK-2817"]["leti_od"] is not None and letadla["OK-2817"]["nedavni"] == [pilot_id]
    assert letadla["OK-CRA"]["vlecne"]
    ucely = {u["kod"]: u for u in nabidky["ucely"]}
    assert [f["kod"] for f in ucely["VYCVIK"]["funkce"]] == ["ZAK"]
    assert ucely["NORMALNI"]["funkce"] == []
    assert nabidky["zpusob_kluzaku"] == "NAVIJAK"


def test_nabidky_opravneni(conn, pilot, osoba, flotila):
    """U osoby role, které smí zastat podle oprávnění a jeho kategorií (db/024)."""
    pilot_id, k = pilot
    vlekar = osoba("Vlekar", ucet=False)
    nikdo = osoba("Nikdo", ucet=False)
    instruktor = conn.execute(
        """INSERT INTO lkkl.lov_opravneni (kod, nazev, poradi)
           VALUES ('FI_S', 'FI(S)', 10) RETURNING id"""
    ).fetchone()["id"]
    conn.execute(
        """INSERT INTO lkkl.lov_opravneni_kategorie
           SELECT o.id, k.id FROM lkkl.lov_opravneni o, lkkl.lov_kategorie k
           WHERE (o.kod, k.kod) IN (('FI_S', 'KLUZAK'), ('FI_S', 'LETOUN'), ('VLEKAR', 'LETOUN'))"""
    )
    conn.execute(
        """INSERT INTO lkkl.lov_opravneni_role
           SELECT %s, id FROM lkkl.lov_role WHERE kod = 'INSTRUKTOR'""",
        (instruktor,),
    )
    conn.execute(
        """INSERT INTO lkkl.lov_osoba_opravneni (osoba_id, opravneni_id)
           VALUES (%s, %s), (%s, (SELECT id FROM lkkl.lov_opravneni WHERE kod = 'VLEKAR'))""",
        (pilot_id, instruktor, vlekar),
    )
    # instruktor jen pro kluzáky (letouny smí, ale nemá), vlekař pro letouny
    conn.execute(
        """INSERT INTO lkkl.lov_osoba_opravneni_kategorie
           SELECT oo.osoba_id, oo.opravneni_id, ok.kategorie_id
           FROM lkkl.lov_osoba_opravneni oo
           JOIN lkkl.lov_opravneni_kategorie ok ON ok.opravneni_id = oo.opravneni_id
           JOIN lkkl.lov_kategorie k ON k.id = ok.kategorie_id
           WHERE NOT (oo.opravneni_id = %s AND k.kod = 'LETOUN')""",
        (instruktor,),
    )
    osoby = {o["id"]: o for o in k.get("/api/lety/nabidky").json()["osoby"]}
    assert osoby[pilot_id]["role"] == [{"ucel": "VYCVIK", "funkce": "PIC", "kategorie": "KLUZAK"}]
    # vlekař (role z převodu v 022, 024): vlečný let (bez účelu), PIC, letoun
    assert osoby[vlekar]["role"] == [{"ucel": None, "funkce": "PIC", "kategorie": "LETOUN"}]
    assert osoby[nikdo]["role"] == []
    # přidání oprávnění a kategorií se zapíše do auditu
    pocty = conn.execute(
        """SELECT count(*) FILTER (WHERE tabulka = 'lov_osoba_opravneni') AS opravneni,
                  count(*) FILTER (WHERE tabulka = 'lov_osoba_opravneni_kategorie') AS kategorie
           FROM lkkl.audit"""
    ).fetchone()
    assert pocty == {"opravneni": 2, "kategorie": 2}


def test_osoba_jen_v_jednom_letu(conn, pilot, osoba, flotila):
    """Kdo je na palubě ve vzduchu, nemůže zároveň vzlétnout jinde; plánovat jde."""
    pilot_id, k = pilot
    k.post("/api/lety", json=_novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, pob=1,
                                   akce="vzlet"))  # fmt: skip
    planovany = k.post(
        "/api/lety",
        json=_novy(conn, rejstrik="OK-3819", posadka={"PIC": pilot_id}, pob=1, akce="naplanovat"),
    )
    assert planovany.status_code == 200
    odpoved = k.post(f"/api/lety/{planovany.json()['let_id']}/vzlet")
    assert odpoved.status_code == 400
    assert re.fullmatch(
        r"Jan Pilot už letí na OK-2817 \(vzlet \d\d:\d\d UTC\)\.",
        odpoved.json()["detail"],
    )

    # Dozor je na zemi – ten se nepočítá.
    zak = osoba("Zak")
    solo = _novy(
        conn, rejstrik="OK-CRA", ucel="VYCVIK_SOLO", posadka={"PIC": zak, "DOZOR": pilot_id},
        zpusob="VLASTNI", akce="vzlet",
    )  # fmt: skip
    conn.execute(
        """INSERT INTO lkkl.lov_osnova (kod, nazev, poradi) VALUES ('O', 'Osnova', 1);
           INSERT INTO lkkl.lov_uloha (kod, nazev, poradi, osnova_id)
           SELECT 'U', 'Úloha', 1, id FROM lkkl.lov_osnova WHERE kod = 'O';
           INSERT INTO lkkl.lov_uloha_ucel (uloha_id, ucel_id)
           SELECT ul.id, u.id FROM lkkl.lov_uloha ul, lkkl.lov_ucel u
           WHERE ul.kod = 'U' AND u.kod = 'VYCVIK_SOLO'"""
    )
    solo["uloha_id"] = _id(conn, "lov_uloha", "U")
    assert k.post("/api/lety", json=solo).status_code == 200


def test_probehly_let_se_prekryva(conn, pilot, let, flotila):
    pilot_id, k = pilot
    let("OK-2817", {"PIC": pilot_id}, vzlet="now() - interval '2 hours'",
        pristani="now() - interval '1 hour'")  # fmt: skip
    casy = conn.execute(
        "SELECT now() - interval '90 minutes' AS v, now() - interval '30 minutes' AS p"
    ).fetchone()
    data = _novy(
        conn, rejstrik="OK-3819", posadka={"PIC": pilot_id}, pob=1, akce="probehly",
        cas_vzletu=casy["v"].isoformat(), cas_pristani=casy["p"].isoformat(),
    )  # fmt: skip
    odpoved = k.post("/api/lety", json=data)
    # (hláška jmenuje druhý z letů, které se překrývají – podle toho, který se kontroloval první)
    assert odpoved.status_code == 400
    assert re.fullmatch(
        r"Jan Pilot je v tu dobu na palubě OK-(2817|3819) "
        r"\(\d\d:\d\d–\d\d:\d\d UTC\)\.",
        odpoved.json()["detail"],
    )

    # Stejné letadlo: hláška jmenuje let, se kterým se překrývá.
    data["letadlo_id"] = conn.execute(
        "SELECT id FROM lkkl.lov_letadlo WHERE rejstrik = 'OK-2817'"
    ).fetchone()["id"]
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 400
    assert re.fullmatch(
        r"OK-2817 má v tu dobu jiný let \(\d\d:\d\d–\d\d:\d\d UTC, PIC Jan Pilot\)\.",
        odpoved.json()["detail"],
    )


def test_doba_nejmene_minuta(conn, pilot, let):
    pilot_id, k = pilot
    let_id = let("OK-CRA", {"PIC": pilot_id}, zpusob="VLASTNI", vzlet="now()")
    k.post(f"/api/lety/{let_id}/pristani")  # v transakci testu stejný čas = 0 s
    doba = conn.execute(
        "SELECT doba_min, doba_uctovana_min FROM lkkl.v_let WHERE id = %s", (let_id,)
    ).fetchone()
    assert doba == {"doba_min": 1, "doba_uctovana_min": 1}


def test_zruseni_vleku_po_vzletu_jen_jeden(conn, pilot, osoba, let):
    """Kluzák po přetrženém laně se zruší, vlečná letí dál."""
    pilot_id, k = pilot
    vlekar = osoba("Vlekar")
    vlecna = let("OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI", vzlet="now()")
    kluzak = let("OK-3819", {"PIC": pilot_id}, zpusob="VLEK", vlecny_let_id=vlecna, vzlet="now()")
    preruseny = _id(conn, "lov_duvod_zruseni", "PRERUSENY_VZLET")
    assert k.post(f"/api/lety/{kluzak}/zrusit", json={"duvod_id": preruseny}).status_code == 200
    assert _stav(conn, kluzak)["stav"] == "ZRUSEN"
    assert _stav(conn, vlecna)["stav"] == "VE_VZDUCHU"


def test_novy_let_mista(conn, pilot, flotila):
    pilot_id, k = pilot
    letnany = _id(conn, "lov_letiste", "LKLT")
    casy = conn.execute(
        "SELECT now() - interval '50 minutes' AS v, now() - interval '10 minutes' AS p"
    ).fetchone()
    data = _novy(
        conn, rejstrik="OK-CRA", zpusob="VLASTNI", posadka={"PIC": pilot_id}, pob=1,
        akce="probehly", cas_vzletu=casy["v"].isoformat(), cas_pristani=casy["p"].isoformat(),
        misto_vzletu_id=letnany, misto_pristani_popis="  pole u Slaného ",
    )  # fmt: skip
    odpoved = k.post("/api/lety", json=data)
    assert odpoved.status_code == 200, odpoved.text
    let = conn.execute(
        "SELECT misto_vzletu, misto_pristani FROM lkkl.v_let WHERE id = %s",
        (odpoved.json()["let_id"],),
    ).fetchone()
    assert let == {"misto_vzletu": "LKLT", "misto_pristani": "pole u Slaného"}
    # Nezadané místo vzletu = domovské letiště.
    plan = _novy(conn, rejstrik="OK-2817", posadka={"PIC": pilot_id}, pob=1, akce="naplanovat")
    plan_id = k.post("/api/lety", json=plan).json()["let_id"]
    assert (
        _id(conn, "lov_letiste", "LKKL")
        == conn.execute(
            "SELECT misto_vzletu_id FROM lkkl.let WHERE id = %s", (plan_id,)
        ).fetchone()["misto_vzletu_id"]
    )
