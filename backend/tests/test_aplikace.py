"""Údaje pro obrazovky, bezpečnostní hlavičky a vracení sestaveného frontendu."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import pripojit_frontend


def test_aplikace_bez_prihlaseni(klient):
    odpoved = klient().get("/api/aplikace")
    assert odpoved.status_code == 200
    assert odpoved.json() == {"verze": "vyvoj", "pruh": "VÝVOJ – lokální databáze"}


def test_bezpecnostni_hlavicky(klient):
    hlavicky = klient().get("/api/aplikace").headers
    assert hlavicky["x-frame-options"] == "DENY"
    assert hlavicky["referrer-policy"] == "same-origin"
    assert "default-src 'self'" in hlavicky["content-security-policy"]


def test_frontend(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<p>aplikace</p>")
    (tmp_path / "assets" / "app-1a2b.js").write_text("// skript")
    (tmp_path.parent / "tajne.txt").write_text("mimo")
    aplikace = FastAPI()
    pripojit_frontend(aplikace, tmp_path)
    k = TestClient(aplikace)

    # Adresy obrazovek vrátí index.html (cestu vyřeší frontend), nikdy z mezipaměti.
    for adresa in ("/", "/prihlaseni", "/heslo?klic=abc"):
        odpoved = k.get(adresa)
        assert odpoved.text == "<p>aplikace</p>", adresa
        assert odpoved.headers["cache-control"] == "no-cache"
    assert k.get("/assets/app-1a2b.js").text == "// skript"
    assert k.head("/prihlaseni").status_code == 200  # hlídání dostupnosti se ptá hlavičkou
    # Chybějící soubor, neznámé rozhraní a soubory mimo složku frontendu = 404.
    assert k.get("/favicon.ico").status_code == 404
    assert k.get("/api/neexistuje").status_code == 404
    assert k.get("/..%2Ftajne.txt").status_code == 404


def test_bez_frontendu_nic(tmp_path):
    aplikace = FastAPI()
    pripojit_frontend(aplikace, tmp_path)
    assert TestClient(aplikace).get("/").status_code == 404
