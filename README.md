# LKKL Log

Evidence letů aeroklubu LKKL: start a přistání z mobilu, přehled dne, opravy s historií,
výpisy a exporty pro účetnictví. Poběží na `https://lety.lkkl.cz`.

Návrh aplikace (co a proč): [docs/navrh.md](docs/navrh.md)

## Stav

| Etapa | Obsah | Stav |
|---|---|---|
| 0 | Kostra, Docker, CI | lokálně hotovo, chybí nasazení na server |
| 1 | Datový model, administrace, import číselníků | hotovo |
| 2 | Přihlášení a role | – |
| 3 | Přehled dne, nový let, vzlet, přistání | – |

## Struktura

```
backend/    Django (Python 3.14, uv) – API, administrace, databázový model
  config/     nastavení, adresy, API (Django Ninja)
  osoby/      osoby (= uživatelé) a jejich oprávnění
  lety/       letadla, letiště, úlohy, lety, posádka, auditní log, uzávěrky
  tests/      testy (pytest, běží proti PostgreSQL)
frontend/   React + TypeScript + Vite + Mantine
docs/       návrh aplikace
compose.yaml       provoz (server): aplikace + databáze
compose.dev.yaml   vývoj: jen databáze
Dockerfile         jeden image: sestavený frontend + backend
```

## Lokální vývoj

Potřeba: Docker Desktop, [uv](https://docs.astral.sh/uv/), Node.js 24.

1. Databáze v Dockeru:

   ```bash
   docker compose -f compose.dev.yaml up -d
   ```

2. Backend (vytvořte `backend/.env` s řádky `DJANGO_DEBUG=1` a
   `DATABASE_URL=postgres://lkkllog:lkkllog@127.0.0.1:5432/lkkllog`):

   ```bash
   cd backend
   uv sync
   uv run python manage.py migrate
   uv run python manage.py createsuperuser
   uv run python manage.py runserver
   ```

   Administrace: http://127.0.0.1:8000/admin/ · API dokumentace: http://127.0.0.1:8000/api/docs

3. Frontend (v druhém terminálu):

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

   Aplikace: http://localhost:5173 (volání `/api` a `/admin` Vite přeposílá na Django).

> Na Windows používejte v `DATABASE_URL` adresu `127.0.0.1`, ne `localhost` – jinak se
> spojení s databází v Dockeru může zaseknout na IPv6.

## Testy a kontrola kódu

```bash
cd backend
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

```bash
cd frontend
npm run lint && npm run build
```

## Číselníky (úvodní načtení)

```bash
cd backend
uv run python manage.py sablona_ciselniku ciselniky.xlsx   # prázdná šablona s návodem
uv run python manage.py nacti_ciselniky ciselniky.xlsx     # načtení (při chybě se nezmění nic)
```

Soubory `*.xlsx` se necommitují (obsahují jména lidí).

## Zkouška celé aplikace v Dockeru

```bash
cp .env.example .env    # vyplnit hesla, APP_IMAGE=lkkllog:local
docker compose build
docker compose up -d
docker compose run --rm web python manage.py migrate
```
