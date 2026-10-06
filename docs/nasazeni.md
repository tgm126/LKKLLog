# Nasazení nové verze

> **NÁVRH ke schválení.** Po schválení se podle něj připraví CI a server.

Nová verze **nahradí** první verzi: převezme její Docker aplikaci na `lety.lkkl.cz`, repozitář
ve VPS Centru i databázi `lkkllog`. Po první verzi na serveru nic nezůstane; její kód je jen
ve větvi `v1` (značka `v1-final`) jako zdroj znalostí. Fáze testování 1 běží rovnou na
`lety.lkkl.cz` – účty se aktivují postupně, dokud je aktivní jen účet uživatele, testuje jen on.

## 1. Jak to bude fungovat

```
commit do main  → GitHub Actions: kontroly a testy (nic se nenasazuje)
značka v2.<modul>.<oprava>
  └► GitHub Actions: kontroly, testy, zkušební sestavení Docker image
     └► git push do repozitáře aplikace ve VPS Centru (+ soubor VERZE)
        └► VPS Centrum sestaví image z Dockerfile a restartuje kontejner
           └► při startu: migrace databáze (SQL skripty db/), pak server
```

Stejný princip jako u první verze (osvědčil se). Značky `v2.*` se nepletou se starými
`v0.*` ani s archivní `v1-final`.

## 2. Server (VPS Centrum, `one12`)

| Co | Stav |
|---|---|
| Aplikace | stávající Docker aplikace `lkkllog` na `lety.lkkl.cz` (proxy a HTTPS už nastavené) |
| Repozitář | stávající `…/lkkllog-lkkl.cz.git`, klíč `VPSC_SSH_KEY` v GitHubu už je |
| Databáze | stávající **`lkkllog`**, schéma **`lkkl`**; připojení unixovým socketem a `DB_*` jako dosud |
| Proměnné | uživatel ve VPS Centru: smazat `DJANGO_*` a další proměnné první verze, přidat `LKKL_PROSTREDI=produkce`, `LKKL_TAJNY_KLIC` (nový), `LKKL_ADRESA=https://lety.lkkl.cz` |

Server čte `DB_*` (socket) i `LKKL_DATABAZE` (lokální vývoj) – úprava `app/nastaveni.py`.

## 3. Úklid po první verzi

1. **Záloha** celé databáze `lkkllog` (`pg_dump`) a stažení mimo server (do
   `C:\GIT\LKKLLog-zalohy`).
2. **Smazání tabulek první verze** ve schématu `public` (seznam `docs/tabulky-v1.md`) a její
   funkce triggeru. **Rozšíření `btree_gist` zůstává** – potřebuje ho nová verze.
3. **Cron** první verze (`/etc/cron.d/lkkllog`, skript údržby) pryč; údržbu nové verze
   (úklid prošlých relací) přidá její vlastní cron.
4. Totéž lokálně: tabulky první verze z lokální databáze pryč (po záloze).

Kroky 1–3 na serveru proběhnou v jedné SSH relaci, až je uživatel výslovně odsouhlasí.

## 4. Migrace databáze

- Spouštěč migrací (`app/migrace.py`) při startu kontejneru projde skripty `db/NNN_*.sql`
  (bez `_data`), porovná je s tabulkou **`lkkl.migrace`** (skript, kdy, otisk obsahu)
  a provede jen nové – každý ve vlastní transakci; při chybě se server nespustí.
- Změna už provedeného skriptu se odhalí podle otisku (chyba místo tichého rozjetí).
- **Lokálně** se `lkkl.migrace` jednou naplní skripty 001–016 (už provedené ručně); dál se
  i lokálně migruje spouštěčem: `uv run python -m app.migrace`.

## 5. Data

Při **prvním** nasazení se data schématu `lkkl` z lokální databáze (letadla, letiště, osoby,
účty, číselníky, osnovy…) přenesou výpisem (`pg_dump --data-only`) na server v jedné SSH
relaci. Potom je pravdou o datech **serverová** databáze; lokální slouží jen pro vývoj a testy.

## 6. CI (GitHub Actions)

- **Každý commit do main:** ruff, testy serveru proti PostgreSQL ve službě CI; od modulu lety
  i lint, stylelint, sestavení frontendu a klikací testy.
- **Značka `v2.*`:** totéž + sestavení image + nasazení.

## 7. První krok

Rozchodit celý řetězec **hned s tím, co máme** (server + přihlašování, bez obrazovek) a ověřit
na `https://lety.lkkl.cz/api/zdravi` (nový endpoint: verze a spojení s databází). Do té doby,
než přijde přihlašovací obrazovka s modulem lety, bude na adrese jen rozhraní.

## 8. Otázky

1. **Smazání dat první verze** na serveru (po úplné záloze) – souhlasíte?
2. **Značky** `v2.<modul>.<oprava>` – souhlasíte?
3. **Skripty 001–016** nechat, jak vznikaly (doporučuji), nebo sloučit?
4. **Data po prvním nasazení** se zadávají na serveru (ruční úpravy přes správce databází
   ve VPS Centru) – souhlasíte?
