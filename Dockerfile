# Jeden image s celou aplikací: sestavený React frontend + Django backend.

# 1) Sestavení frontendu (Node je potřeba jen tady, do výsledného image se nedostane)
FROM node:24-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# 2) Backend
FROM python:3.14-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# Ne /app: tam VPS Centrum připojuje složku s nahraným zdrojovým kódem.
WORKDIR /srv/lkkllog
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ ./
COPY --from=frontend /frontend/dist /srv/lkkllog/frontend_dist
RUN DJANGO_SECRET_KEY=build-only python manage.py collectstatic --noinput

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

RUN useradd --system --uid 10001 --create-home aplikace
USER aplikace
# VPS Centrum může kontejner spustit pod jiným uživatelem – domovská složka musí být zapisovatelná.
ENV HOME=/tmp
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3)"
ENTRYPOINT ["sh", "/srv/lkkllog/docker-entrypoint.sh"]
CMD ["gunicorn", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", \
     "--access-logfile", "-"]
