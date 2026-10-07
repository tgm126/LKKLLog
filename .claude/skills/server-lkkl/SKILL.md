---
name: server-lkkl
description: Práce se serverem LKKL Log ve VPS Centru (vas-hosting, ssh one12) – dotazy do serverové databáze lkkllog, stav a logy Docker kontejneru, zálohy, nástroje VPS Centra. Použij, když potřebuješ něco zjistit na serveru lety.lkkl.cz nebo diagnostikovat výpadek (jen v projektu LKKL Log).
---

# Server LKKL Log (vas-hosting, VPS Centrum)

- Aplikace: `https://lety.lkkl.cz`, stav `GET /api/health` → `{"stav":"ok","verze":"v2.x.y"}`.
- Server: `ssh one12` (one12.vas-server.cz). Docker kontejner `vpsc-app-lkkl-cz-lkkllog`,
  databáze PostgreSQL 17 `lkkllog`, schéma `lkkl`.
- **Pravdou o datech je serverová DB** – data uživatele jen **číst**. Změny dat dělá
  uživatel (nebo migrace při nasazení); ruční `UPDATE` jen na výslovný pokyn a se zálohou.
  Migrace nikdy ručně přes psql (skill `nasazeni`, `migrace-db`).

## SSH: jedno spojení
fail2ban banuje rychlá opakovaná spojení → **všechny příkazy sloučit do jednoho `ssh`**
(více `-c` pro psql, `;` mezi příkazy). Mezi dvěma spojeními nech pár sekund.

## Dotaz do databáze (jen čtení)
```bash
ssh one12 "runuser -u postgres -- psql -d lkkllog -X -A -t \
  -c \"SELECT max(skript) FROM lkkl.migrace\" \
  -c \"SELECT count(*) FROM lkkl.let\""
```
Uvozovky: vnější `"…"` pro ssh, vnitřní `\"…\"` pro psql; `$` v SQL escapovat `\$`.
Výstupy s osobními údaji neopisovat do dokumentů v gitu.

## Záloha (před každou změnou struktury i před nasazením)
```bash
ssh one12 'runuser -u postgres -- pg_dump -Fc lkkllog' \
  > /c/GIT/LKKLLog-zalohy/server-lkkllog-<duvod>-$(date +%Y-%m-%d-%H%M).dump
```
Zálohy jsou mimo git (osobní údaje). Lokální `pg_restore` je PostgreSQL 18 – dump 17 obnoví.

## Kontejner a logy
```bash
ssh one12 'docker ps -a --format "{{.Names}}|{{.Status}}" | grep lkkl; docker logs --tail 40 vpsc-app-lkkl-cz-lkkllog 2>&1'
```
- `Restarting (1)` + v logu „Migrace selhala: …“ → padá migrace při startu; data jsou
  v pořádku (transakce). Řešení přes skill `nasazeni` (kap. „Když to selže“).
- `Up … (healthy)` = běží.
- Nástroje VPS Centra (MCP `vpsc_*`, server `one12.vas-server.cz`): logy nginx, postgres,
  fail2ban, stav služeb – načíst přes ToolSearch, když ssh nestačí.

## Nasazení
Kód se na server dostává jen přes GitHub Actions (značka `v2.*` → push do repozitáře VPS
Centra → sestavení image → restart kontejneru → migrace při startu). Ne ručně.
