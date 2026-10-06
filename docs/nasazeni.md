# Nasazení nové verze

> **Schváleno 6. 10. 2026.** Data první verze se po úplné záloze smažou; značky `v2.*`;
> skripty 001–016 zůstávají, jak vznikaly; po prvním nasazení se data zadávají na serveru.

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
na `https://lety.lkkl.cz/api/health` (nový endpoint: verze a spojení s databází). Do té doby,
než přijde přihlašovací obrazovka s modulem lety, bude na adrese jen rozhraní.

## 8. Stav (6. 10. 2026)

- **Nová verze běží** na `https://lety.lkkl.cz` (značka `v2.1.1`; `v2.1.0` padala – VPS Centrum
  spouští kontejner z `/app`, oprava: `PYTHONPATH` v Dockerfile).
- **Úklid po první verzi hotový:** úplná záloha serverové databáze
  (`C:\GIT\LKKLLog-zalohy\server-lkkllog-v1-2026-10-06.dump`), cron první verze odstraněn,
  tabulky první verze na serveru i lokálně smazané (lokální záloha
  `lokalni-lkkllog-cela-2026-10-06-113111.dump`); `btree_gist` zůstává.
- **Data přenesena** z lokální databáze do schématu `lkkl` na serveru (jedna transakce).
- Proměnné první verze ve VPS Centru smazané (uživatel).
- Zbývá: cron nové verze (úklid relací).
