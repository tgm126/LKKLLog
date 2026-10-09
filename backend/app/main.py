"""Aplikace FastAPI. Spuštění pro vývoj: uv run uvicorn app.main:app --reload"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from psycopg import Connection

from . import db, letadla, lety, muj_provoz, osoby, prihlasovani, sprava, vycvik
from .nastaveni import nastaveni

BEZPECNE_METODY = {"GET", "HEAD", "OPTIONS"}
# Prohlížeč smí načítat jen z vlastní adresy; stránku nejde vložit do cizí (rámeček).
# Referrer jen v rámci aplikace – adresa s klíčem pro nastavení hesla nesmí odejít jinam.
HLAVICKY = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "same-origin",
    "X-Frame-Options": "DENY",
}
CSP = (
    "default-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; "
    "form-action 'self'"
)


log = logging.getLogger("lkkl")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.otevrit(nastaveni.databaze)
    with db.pripojeni() as conn:  # prošlé relace uklízí aplikace sama (i při přihlášení)
        log.info("Smazáno prošlých relací: %d", prihlasovani.smazat_prosle_relace(conn))
    yield
    db.zavrit()


app = FastAPI(
    title="LKKL Log",
    lifespan=lifespan,
    docs_url="/api/docs" if nastaveni.vyvoj else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if nastaveni.vyvoj else None,
)


@app.middleware("http")
async def kontrola_puvodu(request: Request, call_next):
    """Ochrana proti podvrženým požadavkům (CSRF): co něco mění, musí přijít z povolené adresy."""
    if (
        request.method not in BEZPECNE_METODY
        and request.headers.get("origin", "").rstrip("/") not in nastaveni.povolene_adresy
    ):
        return JSONResponse({"detail": "Požadavek z nepovolené adresy."}, status_code=403)
    return await call_next(request)


@app.middleware("http")
async def bezpecnostni_hlavicky(request: Request, call_next):
    odpoved = await call_next(request)
    odpoved.headers.update(HLAVICKY)
    cesta = request.url.path
    if not cesta.startswith("/api/docs"):  # dokumentace rozhraní (jen vývoj) načítá skripty z CDN
        odpoved.headers["Content-Security-Policy"] = CSP
    if not nastaveni.vyvoj:
        odpoved.headers["Strict-Transport-Security"] = "max-age=31536000"
    if cesta.startswith("/assets/"):  # soubory s otiskem obsahu v názvu se nemění
        odpoved.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return odpoved


app.include_router(prihlasovani.router)
app.include_router(lety.router)
app.include_router(osoby.router)
app.include_router(muj_provoz.router)
app.include_router(letadla.router)
app.include_router(sprava.router)
app.include_router(vycvik.router)


@app.get("/api/health")
def health(conn: Connection = Depends(db.spojeni)):
    """Kontrola stavu pro nasazení a hlídání dostupnosti: verze a spojení s databází."""
    conn.execute("SELECT 1")
    return {"stav": "ok", "verze": nastaveni.verze}


# Žlutý pruh: testovací provoz podle nastavení v databázi (lkkl.nastaveni), lokálně vývoj.
PRUH_TEST = "TESTOVACÍ PROVOZ"
PRUH_VYVOJ = "VÝVOJ – lokální databáze"


@app.get("/api/aplikace")
def aplikace(conn: Connection = Depends(db.spojeni)):
    """Co obrazovky ukazují i bez přihlášení: verze a text pruhu (testovací provoz)."""
    test = conn.execute("SELECT testovaci_provoz FROM lkkl.nastaveni").fetchone()[
        "testovaci_provoz"
    ]
    pruh = PRUH_VYVOJ if nastaveni.vyvoj else PRUH_TEST if test else ""
    return {"verze": nastaveni.verze, "pruh": pruh}


def pripojit_frontend(aplikace: FastAPI, slozka: Path) -> None:
    """Server vrací i sestavený frontend (jedna adresa pro obrazovky i rozhraní).

    Adresy obrazovek (/, /prihlaseni, /heslo…) dostanou index.html a cestu vyřeší frontend;
    neexistující soubor (s příponou) a neznámá adresa pod /api vrátí 404.
    """
    index = slozka / "index.html"
    if not index.is_file():
        return
    koren = slozka.resolve()
    aplikace.mount("/assets", StaticFiles(directory=slozka / "assets"), name="assets")

    @aplikace.api_route("/{cesta:path}", methods=["GET", "HEAD"], include_in_schema=False)
    def frontend(cesta: str):
        if cesta == "api" or cesta.startswith("api/"):
            raise HTTPException(404, "Neexistuje.")
        soubor = (koren / cesta).resolve()
        if cesta and soubor.is_relative_to(koren) and soubor.is_file():
            return FileResponse(soubor)
        if "." in cesta.rsplit("/", 1)[-1]:
            raise HTTPException(404, "Neexistuje.")
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


pripojit_frontend(app, nastaveni.frontend)
