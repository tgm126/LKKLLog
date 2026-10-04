# LKKL Log – pokyny pro vývoj

- Návrh aplikace je v `docs/navrh.md` – při změnách chování ho udržuj aktuální.
- Komunikace s uživatelem česky; odborné výrazy vysvětlit jednou větou.
- Doménové názvy (modely, pole, proměnné) česky bez diakritiky podle návrhu
  (`Let`, `Posadka`, `cas_vzletu`, `platce`…); technické věci anglicky.
- Backend: Django 6 + Django Ninja, Python 3.14, závislosti přes `uv`
  (`uv add`, `uv run`). Testy pytest proti PostgreSQL (`compose.dev.yaml`).
- Pravidla, která jdou hlídat v databázi, patří do databáze (constraints, generated
  field `doba_min`, trigger auditního logu). Python `round()` pro dobu letu nepoužívat.
- Všechny časy v UTC. Let se nikdy nemaže (jen `stav=zrusen` s důvodem), číselníky se
  jen deaktivují.
- Oprávnění vždy kontrolovat na serveru, ne jen ve frontendu.
- Na Windows v `DATABASE_URL` používat `127.0.0.1`, ne `localhost`.
- Před commitem: `uv run ruff check . && uv run ruff format --check . && uv run pytest`
  (v `backend/`) a `npm run lint && npm run build` (ve `frontend/`).
- Server: aplikace běží jako Docker aplikace ve VPS Centru (jeden kontejner z `Dockerfile`,
  databáze PostgreSQL serveru přes `DB_*` proměnné a unixový socket, migrace při startu
  přes `DJANGO_MIGRATE_ON_START=1`).
- VPS Centrum v nginx blokuje cesty a subdomény `config|tmp|temp|log|logs|bin|inc` (403) –
  tyto názvy nepoužívat v URL aplikace.
- E-maily členům: režim odesílání (vypnuto / jen povolené adresy / všem, viz návrh kap. 9.1);
  pozvánky jen ruční akcí admina (vybraným nebo všem), nikdy automaticky při založení osoby.
- Telefon osoby: nikdy v seznamech, číselnících ani na displeji; jen na vyžádání
  (samostatné volání API po ťuknutí na „Zobrazit telefon“), pro všechny přihlášené.
- Klikací testy v prohlížeči (Playwright): `backend/e2e`, spuštění `uv run pytest e2e`
  (frontend musí být sestavený). Běží v CI a nasazení čeká, až projdou. Před čekáním na
  prvek po přechodu stránky vždy ověřit nadpis nové stránky (jinak hrozí souběh).
