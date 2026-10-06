"""Aplikace FastAPI. Spuštění pro vývoj: uv run uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import Connection

from . import db, prihlasovani
from .nastaveni import nastaveni

BEZPECNE_METODY = {"GET", "HEAD", "OPTIONS"}


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.otevrit(nastaveni.databaze)
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


app.include_router(prihlasovani.router)


@app.get("/api/health")
def health(conn: Connection = Depends(db.spojeni)):
    """Kontrola stavu pro nasazení a hlídání dostupnosti: verze a spojení s databází."""
    conn.execute("SELECT 1")
    return {"stav": "ok", "verze": nastaveni.verze}
