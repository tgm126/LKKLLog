"""Přihlášení jen ke čtení – sdílený počítač (docs/modul-desktop.md 6.1, db/030)."""

import re

from app.main import app
from app.prihlasovani import JEN_CTENI

from .conftest import HESLO

# Zápisy, které relaci nepotřebují (přihlášení, odhlášení, nastavení hesla odkazem).
BEZ_RELACE = {"/api/prihlaseni", "/api/odhlaseni", "/api/heslo/nastavit"}


def _jen_cteni(klient, email: str):
    k = klient()
    odpoved = k.post("/api/prihlaseni", json={"email": email, "heslo": HESLO, "jen_cteni": True})
    assert odpoved.status_code == 200, odpoved.text
    assert odpoved.json()["jen_cteni"] is True
    return k


def test_jen_cteni_cte_bez_prav(klient, osoba, flotila):
    osoba("Admin", admin=True)
    k = _jen_cteni(klient, "admin@example.cz")
    ja = k.get("/api/ja").json()
    assert ja["jen_cteni"] is True
    # práva se v relaci jen ke čtení neuplatní (ani admin)
    assert not any(ja["prava"].values())
    assert k.get("/api/lety").status_code == 200
    assert k.get("/api/ucty").status_code == 403


def test_bezne_prihlaseni_neni_jen_cteni(prihlasit, osoba):
    osoba("Pilot")
    ja = prihlasit("pilot@example.cz").get("/api/ja").json()
    assert ja["jen_cteni"] is False


def test_jen_cteni_zadny_zapis(klient, osoba, flotila):
    """Každý zápis aplikace (mimo přihlášení a odhlášení) server v relaci jen ke čtení
    odmítne – i ten, který přibude později, protože všechny jdou přes `prihlaseny`."""
    osoba("Admin", admin=True)
    k = _jen_cteni(klient, "admin@example.cz")
    # všechny adresy aplikace z popisu rozhraní (OpenAPI), parametry cesty = 1
    zapisy = [
        (metoda.upper(), re.sub(r"\{[^}]+\}", "1", cesta))
        for cesta, metody in app.openapi()["paths"].items()
        if cesta not in BEZ_RELACE
        for metoda in metody
        if metoda not in ("get", "head")
    ]
    assert len(zapisy) > 20  # kontrola, že se zápisy opravdu našly
    for metoda, cesta in zapisy:
        odpoved = k.request(metoda, cesta, json={})
        assert odpoved.status_code == 403, (metoda, cesta, odpoved.status_code)
        assert odpoved.json()["detail"] == JEN_CTENI


def test_jen_cteni_odhlaseni(klient, osoba):
    osoba("Pilot")
    k = _jen_cteni(klient, "pilot@example.cz")
    assert k.post("/api/odhlaseni").status_code == 204
    assert k.get("/api/ja").status_code == 401
