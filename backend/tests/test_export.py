"""Export záznamů o letech – PDF e-mailem adminům (docs/modul-export.md)."""

import io
import smtplib

import pytest
from pypdf import PdfReader


def _text_pdf(zprava) -> tuple[str, str]:
    [priloha] = list(zprava.iter_attachments())
    obsah = priloha.get_content()
    assert obsah.startswith(b"%PDF")
    text = " ".join(s.extract_text() for s in PdfReader(io.BytesIO(obsah)).pages)
    # zalomení v buňkách se ve vytaženém textu projeví různě – porovnává se bez mezer
    return priloha.get_filename(), "".join(text.split())


@pytest.fixture
def provoz(conn, osoba, let):
    """Dnešní provoz: aerovlek, výcvik na soukromém kluzáku (hradí pilot), let ve vzduchu
    a zrušený let; let před 40 dny (jiný den i měsíc)."""
    pilot, vlekar, instruktor, zak, dalsi = (
        osoba(p) for p in ("Pilot", "Vlekar", "Instruktor", "Zak", "Dalsi")
    )
    conn.execute("UPDATE lkkl.lov_letadlo SET soukrome = true WHERE rejstrik = 'OK-2817'")
    vlecna = let(
        "OK-CRA", {"PIC": vlekar}, ucel=None, zpusob="VLASTNI",
        vzlet="now() - interval '50 minutes'", pristani="now() - interval '42 minutes'",
    )  # fmt: skip
    kluzak = let(
        "OK-3819", {"PIC": pilot}, zpusob="VLEK", vlecny_let_id=vlecna,
        vzlet="now() - interval '50 minutes'", pristani="now() - interval '20 minutes'",
    )  # fmt: skip
    vycvik = let(
        "OK-2817", {"PIC": instruktor, "ZAK": zak}, ucel="VYCVIK", pob=None,
        vzlet="now() - interval '40 minutes'", pristani="now() - interval '30 minutes'",
    )  # fmt: skip
    conn.execute(
        "UPDATE lkkl.let SET plati_aeroklub = false, platce_id = %s, poznamka = 'termika' "
        "WHERE id = %s",
        (zak, vycvik),
    )
    let("OK-CRA", {"PIC": dalsi}, zpusob="VLASTNI", vzlet="now() - interval '5 minutes'")
    let("OK-2817", {"PIC": dalsi}, zrusit=True)
    let(
        "OK-3819",
        {"PIC": dalsi},
        vzlet="now() - interval '40 days'",
        pristani="now() - interval '40 days' + interval '10 minutes'",
    )
    conn.execute("SET CONSTRAINTS ALL IMMEDIATE")
    return conn.execute("SELECT den FROM lkkl.v_let WHERE id = %s", (kluzak,)).fetchone()["den"]


@pytest.fixture
def exportujici(osoba, prihlasit):
    osoba("Admin", admin=True)
    osoba("Bdmin", admin=True)
    osoba("Ucetni", smi_exportovat=True)
    return prihlasit("ucetni@example.cz")


def test_export_dne(conn, provoz, exportujici, schranka):
    odpoved = exportujici.post("/api/export", json={"druh": "DEN", "den": str(provoz)})
    assert odpoved.status_code == 200, odpoved.text
    vysledek = odpoved.json()
    assert vysledek["lety"] == 3
    assert vysledek["adresy"] == ["admin@example.cz", "bdmin@example.cz"]
    assert [z["To"] for z in schranka.odeslane] == vysledek["adresy"]

    zprava = schranka.odeslane[0]
    assert zprava["Subject"] == f"AK Kladno Log – lety {vysledek['obdobi']}"
    assert "Export vyžádal(a): Jan Ucetni." in zprava.get_body().get_content()
    soubor, text = _text_pdf(zprava)
    assert soubor == f"lety-{provoz:%Y-%m-%d}.pdf"
    for ocekavane in (
        vysledek["obdobi"],
        "Aerovlek OK-CRA",  # kluzák: způsob vzletu s vlečnou
        "Vlek OK-3819",  # vlečná: koho vlekla
        "Pilot ve výcviku: Zak Jan",  # další posádka
        "Zak Jan Výcvik",  # hradí, účel
        "soukromé · dopsáno · termika",  # štítky a poznámka
        "Pozor: 1 let není ukončený",
        "Souhrn podle letadel",
        "OK-2817 (soukromé)",
        "Plachtařský provoz celkem 3 3 0:48 1",
        "Zkontroloval",
    ):
        assert "".join(ocekavane.split()) in text, ocekavane
    # skupiny podle letadla (podle rejstříku); Normální, vlastní vzlet a POB se nevypisují
    assert text.index("OK-2817·") < text.index("OK-3819·") < text.index("OK-CRA·")
    assert "OK-CRA·" in text and "1let" in text
    for chybi in ("Normální", "Vlastní", "POB", "plátců"):
        assert chybi not in text, chybi

    zaznam = conn.execute(
        """SELECT adresa, druh, chyba, lower(obdobi) AS od, upper(obdobi) - lower(obdobi) AS dni
           FROM lkkl.email e JOIN lkkl.lov_osoba o ON o.id = e.odeslal_id
           WHERE o.prijmeni = 'Ucetni' ORDER BY adresa"""
    ).fetchall()
    assert [(z["adresa"], z["druh"], z["chyba"], z["od"], z["dni"]) for z in zaznam] == [
        ("admin@example.cz", "EXPORT_LETU", None, provoz, 1),
        ("bdmin@example.cz", "EXPORT_LETU", None, provoz, 1),
    ]

    znovu = exportujici.post("/api/export", json={"druh": "DEN", "den": str(provoz)})
    assert znovu.status_code == 429 and len(schranka.odeslane) == 2


def test_export_mesice(provoz, exportujici, schranka):
    odpoved = exportujici.post("/api/export", json={"druh": "MESIC", "den": str(provoz)})
    assert odpoved.status_code == 200, odpoved.text
    soubor, text = _text_pdf(schranka.odeslane[0])
    assert soubor == f"lety-{provoz:%Y-%m}.pdf"
    assert odpoved.json()["lety"] == 3  # let před 40 dny je v jiném měsíci
    assert "3lety" in text  # nadpis dne


def test_admin_bez_prihlaseni_nedostane(conn, osoba, provoz, exportujici, schranka):
    conn.execute(
        """UPDATE lkkl.ucet SET prihlaseni_povoleno = false
           WHERE osoba_id = (SELECT id FROM lkkl.lov_osoba WHERE prijmeni = 'Bdmin')"""
    )
    odpoved = exportujici.post("/api/export", json={"druh": "DEN", "den": str(provoz)})
    assert odpoved.json()["adresy"] == ["admin@example.cz"]


def test_nabidka(provoz, exportujici):
    nabidka = exportujici.get("/api/export").json()
    assert nabidka["adresy"] == ["admin@example.cz", "bdmin@example.cz"]
    dny = nabidka["dny"]
    assert {"den": str(provoz), "lety": 3} in dny  # jen ukončené
    assert len(dny) == 2


def test_prava(osoba, prihlasit, klient, provoz, schranka):
    osoba("Admin", admin=True)
    osoba("Ucetni", smi_exportovat=True)
    pilot = prihlasit("pilot@example.cz")
    assert pilot.get("/api/export").status_code == 403
    assert pilot.post("/api/export", json={"druh": "DEN", "den": str(provoz)}).status_code == 403
    assert pilot.get("/api/ja").json()["prava"]["smi_exportovat"] is False
    assert prihlasit("admin@example.cz").get("/api/ja").json()["prava"]["smi_exportovat"]

    k = klient()
    k.post(
        "/api/prihlaseni",
        json={"email": "ucetni@example.cz", "heslo": "spravne-heslo-123", "jen_cteni": True},
    )
    assert k.post("/api/export", json={"druh": "DEN", "den": str(provoz)}).status_code == 403
    assert schranka.odeslane == []


def test_bez_letu(provoz, exportujici, schranka):
    odpoved = exportujici.post("/api/export", json={"druh": "DEN", "den": "2020-01-01"})
    assert odpoved.status_code == 400
    assert "nejsou žádné ukončené lety" in odpoved.json()["detail"]
    assert schranka.odeslane == []


def test_chyba_smtp(conn, provoz, exportujici, schranka):
    schranka.chyba = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
    odpoved = exportujici.post("/api/export", json={"druh": "DEN", "den": str(provoz)})
    assert odpoved.status_code == 502
    assert odpoved.json()["detail"].startswith("E-mail se nepodařilo odeslat: admin@example.cz")
    chyby = conn.execute(
        "SELECT count(*) AS n FROM lkkl.email WHERE druh = 'EXPORT_LETU' AND chyba IS NOT NULL"
    ).fetchone()["n"]
    assert chyby == 2
    # neodeslaný export nebrání dalšímu pokusu
    schranka.chyba = None
    znovu = exportujici.post("/api/export", json={"druh": "DEN", "den": str(provoz)})
    assert znovu.status_code == 200
