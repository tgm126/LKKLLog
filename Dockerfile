# Jeden image s celou aplikací: server FastAPI a SQL skripty databáze.
# (Frontend přibude s modulem lety – sestaví se v samostatném kroku a server ho bude vracet.)

FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# Ne /app: tam VPS Centrum připojuje složku s nahraným zdrojovým kódem.
WORKDIR /srv/lkkl/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
# Skripty databáze vedle serveru: spouštěč migrací je hledá v ../db.
COPY db/ /srv/lkkl/db/

# VPS Centrum spouští kontejner pod uživatelem domény a s pracovní složkou /app (připojený
# zdrojový kód) – proto domovská složka v /tmp a balíček serveru na PYTHONPATH (cesty nezávislé
# na pracovní složce).
ENV HOME=/tmp
ENV PYTHONPATH=/srv/lkkl/backend
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"

# Nejdřív migrace (při chybě se server nespustí), pak server. Proxy a HTTPS dělá VPS Centrum.
CMD ["sh", "-c", "python -m app.migrace && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
