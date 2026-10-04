from django.conf import settings
from django.db import connection
from ninja import NinjaAPI, Schema

from osoby.api import router as ucty_router

api = NinjaAPI(title="LKKL Log API", version="1", docs_url="/docs" if settings.DEBUG else None)
api.add_router("/ucet", ucty_router)


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
