"""Přehled letů dne a sluneční časy (docs/modul-lety.md)."""

from datetime import UTC, datetime

from app import lety


def test_den_a_slunce(prihlasit, osoba, flotila):
    osoba("Pilot")
    den = prihlasit("pilot@example.cz").get("/api/den", params={"den": "2026-10-06"}).json()
    assert den["den"] == "2026-10-06"
    assert den["letiste"] == {
        "id": den["letiste"]["id"],
        "kod": "LKKL",
        "nazev": "Kladno",
        "domovske": True,
    }
    # Kladno 6. 10. 2026 (UTC): soumrak 04:38, východ 05:11, západ 16:31, konec soumraku 17:04.
    casy = {k: v[11:16] for k, v in den["slunce"].items()}
    assert casy == {"tb": "04:38", "sr": "05:11", "ss": "16:31", "te": "17:04"}


def test_lety_dne(prihlasit, osoba, let):
    pilot, zak = osoba("Pilot"), osoba("Zak")
    vzduch = let(
        "OK-2817",
        {"PIC": pilot, "ZAK": zak},
        ucel="VYCVIK",
        vzlet="now() - interval '10 minutes'",
        pob=None,
    )
    vlecna = let("OK-CRA", {"PIC": pilot}, ucel=None, zpusob="VLASTNI")
    kluzak = let("OK-3819", {"PIC": zak}, zpusob="VLEK", vlecny_let_id=vlecna)
    prelet = let(
        "OK-CRA",
        {"PIC": pilot},
        zpusob="VLASTNI",
        vzlet="now() - interval '2 hours'",
        pristani="now() - interval '1 hour'",
        misto_pristani="LKLT",
    )
    zruseny = let("OK-3819", {"PIC": pilot}, zrusit=True)
    vcera = let(
        "OK-3819",
        {"PIC": pilot},
        vzlet="now() - interval '30 hours'",
        pristani="now() - interval '29 hours'",
    )

    odpoved = prihlasit("pilot@example.cz").get("/api/lety").json()
    pasky = {p["id"]: p for p in odpoved["lety"]}
    assert vcera not in pasky
    assert {pasky[i]["stav"] for i in pasky} == {"VE_VZDUCHU", "NAPLANOVAN", "UKONCEN", "ZRUSEN"}

    v = pasky[vzduch]
    posadka = [(c["prijmeni"], c["funkce_kod"]) for c in v["posadka"]]
    assert posadka == [("Pilot", "PIC"), ("Zak", "ZAK")]
    assert v["pob"] == 2  # u výcviku spočítaný z posádky (PIC + žák)
    assert v["ucel_kod"] == "VYCVIK" and v["zpusob_vzletu_kod"] == "NAVIJAK"
    assert v["misto_vzletu"] is None  # domovské se neuvádí
    # (po konci občanského soumraku má každý let ve vzduchu varování – podle času spuštění testu)
    assert v["varovani"] is None or v["varovani"].startswith("Po konci občanského soumraku")

    assert pasky[kluzak]["vlek_rejstrik"] == "OK-CRA" and pasky[kluzak]["vlecny_let_id"] == vlecna
    assert pasky[vlecna]["je_vlecny"] and pasky[vlecna]["vlek_rejstrik"] == "OK-3819"
    assert pasky[prelet]["misto_pristani"] == "LKLT" and pasky[prelet]["doba_uctovana_min"] == 60
    assert pasky[zruseny]["duvod_zruseni"] is not None


def test_ve_vzduchu_od_vcerejska(prihlasit, osoba, let):
    pilot = osoba("Pilot")
    nocni = let("OK-3819", {"PIC": pilot}, vzlet="now() - interval '30 hours'")
    pasek = prihlasit("pilot@example.cz").get("/api/lety").json()["lety"][0]
    assert pasek["id"] == nocni and "Přes maximální dobu letu (1°00" in pasek["varovani"]


def test_varovani():
    te = datetime(2026, 10, 6, 17, 4, tzinfo=UTC)
    ve_vzduchu = {"stav": "VE_VZDUCHU", "cas_vzletu": datetime(2026, 10, 6, 16, 0, tzinfo=UTC)}
    pozde = datetime(2026, 10, 6, 17, 10, tzinfo=UTC)
    assert lety.varovani({**ve_vzduchu, "max_doba_min": None}, pozde, te) == (
        "Po konci občanského soumraku (TE 17:04)"
    )
    assert lety.varovani({**ve_vzduchu, "max_doba_min": 45}, pozde, None) == (
        'Přes maximální dobu letu (45")'
    )
    assert lety.varovani({**ve_vzduchu, "max_doba_min": None}, te, te) is None
    assert lety.varovani({"stav": "UKONCEN"}, pozde, te) is None


def test_bez_prihlaseni(klient):
    assert klient().get("/api/lety").status_code == 401
    assert klient().get("/api/den").status_code == 401
