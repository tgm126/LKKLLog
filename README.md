# LKKL Log

Evidence letů aeroklubu LKKL: start a přistání z mobilu, přehled dne, opravy s historií,
výpisy a exporty pro účetnictví. Poběží na `https://lety.lkkl.cz`.

Návrh aplikace (co a proč): [docs/navrh.md](docs/navrh.md) · Provoz na serveru: [docs/provoz.md](docs/provoz.md)

## Stav

| Etapa | Obsah | Stav |
|---|---|---|
| 0 | Kostra, Docker, CI, nasazení na server | hotovo |
| 1 | Datový model, administrace, import číselníků | hotovo |
| 2 | Přihlášení, role, pozvánky, nastavení provozu | hotovo |
| 3 | Přehled dne, nový let, vzlet, přistání, dodatečný zápis, zrušení | hotovo |
| 4 | Zálohy: týdenní export e-mailem, ověřená obnova, postup při problému | hotovo |
| 5 | Opravy letů s důvodem, historie změn, tlačítko Zpět | hotovo |
| 6 | Vlek (dvojice kluzák + vlečná), další let odsud (mezipřistání) | hotovo |
| 7 | Výpis letů za období se souhrny, export do Excelu a CSV | hotovo |
| 8 | Denní a měsíční uzávěrky, změny po uzávěrce, přepočet, práva podle uzávěrky | hotovo |
| 9 | Velký displej (TV) bez přihlášení přes tajný odkaz | hotovo |
| 10 | Upozornění na neukončené lety e-mailem a push notifikacemi | hotovo |
| 11 | Můj nálet: osobní součty hodin a startů, seznam a Excel vlastních letů | hotovo |
| 12 | Licence, medical a rozlétanost: správa, přehled, varování při zakládání letu | hotovo |

## Struktura

```
backend/    Django (Python 3.14, uv) – API, administrace, databázový model
  config/     nastavení, adresy, API (Django Ninja)
  osoby/      osoby (= uživatelé) a jejich oprávnění
  lety/       letadla, letiště, úlohy, lety, posádka, auditní log, uzávěrky
  tests/      testy (pytest, běží proti PostgreSQL)
frontend/   React + TypeScript + Vite + Mantine
docs/       návrh aplikace
compose.yaml       zkouška celé aplikace lokálně: aplikace + databáze
compose.dev.yaml   vývoj: jen databáze
Dockerfile         jeden image: sestavený frontend + backend (podle něj staví i VPS Centrum)
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

Klikací testy v prohlížeči (Playwright, potřebují sestavený frontend a běžící databázi):

```bash
cd backend
uv run playwright install chromium   # jednou
uv run pytest e2e
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
