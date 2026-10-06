# Nasazení nové verze

> **NÁVRH ke schválení.** Po schválení se podle něj připraví CI a server.

Cíl: standardní, opakovatelné nasazení nové verze **vedle** první verze. První verze dál běží
na `lety.lkkl.cz` (větev `v1`), nová dostane vlastní adresu. Přepnutí `lety.lkkl.cz` na novou
verzi přijde až s fází 3 (rollout na všechny).

## 1. Jak to bude fungovat

```
commit do main  → GitHub Actions: kontroly a testy (nic se nenasazuje)
značka v2.<modul>.<oprava>
  └► GitHub Actions: kontroly, testy, zkušební sestavení Docker image
     └► git push do repozitáře nové aplikace ve VPS Centru (+ soubor VERZE)
        └► VPS Centrum sestaví image z Dockerfile a restartuje kontejner
           └► při startu: migrace databáze (SQL skripty db/), pak server
```

Stejný princip jako první verze (osvědčil se), ale vlastní aplikace, adresa a značky.

## 2. Server (VPS Centrum, `one12`)

| Co | Návrh |
|---|---|
| Aplikace | nová **Docker aplikace** ve VPS Centru, např. `lkkl` |
| Adresa | nová subdoména **`lety2.lkkl.cz`** (otázka 1) |
| Databáze | stávající **`lkkllog`**, nové **schéma `lkkl`**; tabulky první verze ve `public` zůstávají nedotčené |
| Připojení | stejně jako první verze: unixový socket a proměnné `DB_*` z VPS Centra |
| Proměnné | `LKKL_PROSTREDI=produkce`, `LKKL_TAJNY_KLIC` (nový, jen ve VPS Centru), `LKKL_ADRESA=https://lety2.lkkl.cz`, `LKKL_POVOLENE_ADRESY` |

Server čte `DB_*` (socket) i `LKKL_DATABAZE` (lokální vývoj) – úprava `app/nastaveni.py`.

## 3. Migrace databáze

- Malý spouštěč migrací (`app/migrace.py`) při startu kontejneru projde skripty
  `db/NNN_*.sql` (bez `_data`), porovná je s tabulkou **`lkkl.migrace`** (skript, kdy, otisk
  obsahu) a provede jen ty nové – každý ve vlastní transakci; při chybě se server nespustí.
- Změna už provedeného skriptu se odhalí podle otisku (chyba místo tichého rozjetí).
- **Lokálně** se `lkkl.migrace` jednou naplní skripty 001–016 (už provedené ručně); dál se
  i lokálně migruje spouštěčem: `uv run python -m app.migrace`.
- Před migrací na serveru záloha schématu `lkkl` (`pg_dump`) do složky mimo web.

## 4. Data

Při **prvním** nasazení se data ze schématu `lkkl` lokální databáze (letadla, letiště, osoby,
účty, číselníky…) přenesou výpisem (`pg_dump --data-only`) a nahrají na server v jedné
SSH relaci. Potom je pravdou o datech **serverová** databáze (otázka 4).

## 5. CI (GitHub Actions)

- **Každý commit do main:** ruff, testy serveru proti PostgreSQL ve službě CI; od modulu lety
  i lint, stylelint, sestavení frontendu a klikací testy.
- **Značka `v2.*`:** totéž + sestavení image + nasazení. Archivní značky (`v1-final`) ani
  značky první verze (`v0.*`) novou aplikaci nespustí – workflow reaguje jen na `v2.*`.
- Klíč pro push do VPS Centra: stávající `VPSC_SSH_KEY` (patří uživateli VPS Centra, má přístup
  i k novému repozitáři), adresa repozitáře nové aplikace jako nový údaj.

## 6. První krok

Rozchodit celý řetězec **hned s tím, co máme** (server + přihlašování, bez obrazovek) a ověřit
na `https://lety2.lkkl.cz/api/zdravi` (nový endpoint: verze a spojení s databází). Modul lety
pak už jen přibývá dalšími značkami.

## 7. Co udělá uživatel ve VPS Centru

Docker aplikaci nástroje Váš Hosting neumí založit, proto ručně (krok za krokem popíšu):
1. založit subdoménu a Docker aplikaci, přiřadit databázi `lkkllog`;
2. zadat proměnné prostředí (tajný klíč vygeneruji, předáte ho jen do VPS Centra);
3. poslat mi adresu git repozitáře nové aplikace.

## 8. Otázky

1. **Adresa:** `lety2.lkkl.cz`, nebo jinak (např. `novelety.lkkl.cz`)? Nesmí obsahovat
   `config`, `tmp`, `temp`, `log`, `logs`, `bin`, `inc` (blokuje je VPS Centrum).
2. **Značky** `v2.<modul>.<oprava>` – souhlasíte?
3. **Sloučit skripty 001–016** do jednoho před prvním nasazením (pravidlo 6), nebo je nechat
   tak, jak vznikaly? Doporučuji **nechat** – spouštěč je provede po sobě a historie zůstane
   čitelná; sloučit se dají kdykoli později.
4. **Kde se zadávají data po prvním nasazení:** od té chvíle na serveru (lokální databáze jen
   pro vývoj a testy), souhlasíte? Ruční úpravy pak přes správce databází ve VPS Centru.
