from django.conf import settings
from django.db import connection
from ninja import NinjaAPI, Schema

from ciselniky.api import router as ciselniky_router
from lety.api import router as lety_router
from lety.sluzby import ChybaLetu
from osoby.api import router as ucty_router
from osoby.karta import router as osoby_router

api = NinjaAPI(title="LKKL Log API", version="1", docs_url="/docs" if settings.DEBUG else None)
api.add_router("/ucet", ucty_router)
api.add_router("/sprava/ciselniky", ciselniky_router)
api.add_router("/sprava/osoby", osoby_router)
api.add_router("/", lety_router)


@api.exception_handler(ChybaLetu)
def chyba_letu(request, chyba: ChybaLetu):
    return api.create_response(
        request,
        {"detail": chyba.zprava, "kod": chyba.kod, "let_id": chyba.let_id},
        status=chyba.status,
    )


class HealthOut(Schema):
    status: str
    databaze: bool
    verze: str


@api.get("/health", response=HealthOut, tags=["provoz"])
def health(request):
    """Kontrola stavu – volá ji nasazovací skript po restartu aplikace."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        databaze = True
    except Exception:
        databaze = False
    return {
        "status": "ok" if databaze else "chyba",
        "databaze": databaze,
        "verze": settings.APP_VERSION,
    }
