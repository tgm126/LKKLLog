from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import path, re_path

from .api import api

admin.site.site_header = "LKKL Log – administrace"
admin.site.site_title = "LKKL Log"
admin.site.index_title = "Technická správa"


def frontend(request):
    """Vrátí index.html Reactu pro všechny ostatní adresy (o stránky se stará React)."""
    index = settings.FRONTEND_DIST / "index.html"
    if not index.exists():
        raise Http404("Frontend není sestavený (npm run build).")
    return FileResponse(index.open("rb"), content_type="text/html")


urlpatterns = [
    path("api/", api.urls),
    path("admin/", admin.site.urls),
    re_path(r"^(?!api/|admin/|static/).*$", frontend),
]
