---
name: migrace-db
description: Změna struktury databáze LKKL Log (schéma lkkl) novým skriptem db/NNN_*.sql – záloha, psaní migrace s převodem dat, známé pasti PostgreSQL, spuštění, obnova lokální DB a povinná zkouška na kopii serverových dat. Použij u každé nové tabulky, sloupce, omezení, pohledu nebo triggeru v projektu LKKL Log.
---

# Migrace databáze LKKL Log

Pravidla datového modelu jsou v CLAUDE.md (body 5, 8–12) – tady je postup a pasti.

## 1. Postup
1. **Lokální záloha:** `bash db/zaloha.sh` (do `C:\GIT\LKKLLog-zalohy`).
2. **Nový skript** `db/NNN_nazev.sql` (další číslo). Hlavička: co a proč, odkaz na návrh
   v `docs/`. Provedený skript se nemění (spouštěč hlídá otisk) – oprava = nový skript.
   Výjimka: skript, který ještě **neprošel na serveru**, se smí opravit; lokální DB pak
   obnov ze zálohy (kap. 3).
3. **Spuštění:** `cd backend && uv run python -m app.migrace` (nikdy ručně přes psql).
4. **Kontroly a testy:** `uv run ruff check . && uv run pytest` (testy si DB sestaví samy
   ze skriptů bez `_data`).
5. **Zkouška na kopii serveru** (kap. 4) – povinně před každým nasazením.
6. **Dokumentace:** řádek v `docs/tabulky.md` (objekt, druh, účel, čísla skriptů), případně
   návrh modulu v `docs/`.

## 2. Pasti (na všechny už jsme narazili)
- **Převod dat vs. omezení:** když převod porušuje staré omezení, nejdřív
  `ALTER TABLE … DROP CONSTRAINT`, pak `UPDATE`, pak `ADD CONSTRAINT` s novým pravidlem.
- **Odložené kontroly:** `UPDATE` tabulky `let` (i jiných s `CONSTRAINT TRIGGER … DEFERRABLE`)
  nechá čekající kontroly → další `ALTER TABLE` hlásí „pending trigger events“. Po převodu
  dej `SET CONSTRAINTS ALL IMMEDIATE;`.
- **Převod bez historie:** převod není úprava uživatelem → `ALTER TABLE x DISABLE TRIGGER audit;`
  … `ENABLE TRIGGER audit;` (nebo audit trigger nové tabulky založit až po naplnění).
- **Pohledy:** `SELECT *` v pohledu si nový sloupec nevezme a s odebíraným sloupcem nejde
  `ALTER` → pohledy nad tabulkou `DROP VIEW` a založit znovu. `CREATE OR REPLACE VIEW` smí
  sloupce jen **přidat na konec**.
- **Jména objektů:** jméno nové tabulky může být obsazené indexem (`relace_osoba` byl index
  na `relace.osoba_id`) → ověřit `SELECT relname FROM pg_class WHERE relname = '…'`.
- **Cizí klíče bez kaskády:** mazání nadřízených řádků musí v kódu nejdřív smazat podřízené
  (vzor `smazat_relace` v `backend/app/prihlasovani.py`).
- **Domény v polích:** `array_agg(nazev)` nad doménou `lkkl.nazev` vrací psycopg jako text →
  `nazev::text`; prázdné pole s typem `'{}'::bigint[]`.
- **Data podle kódu:** hodnoty, podle jejichž kódu program uplatňuje pravidla, patří do
  skriptu struktury; ostatní data zadává uživatel (u nových příznaků je migrace smí
  jednorázově nastavit podle zadání uživatele – uvést v komentáři).
- `_data.sql` skripty se při migraci nespouštějí; po změně struktury je přepiš do nového
  tvaru (slouží pro novou databázi a pro e2e přípravu).

## 3. Obnova lokální DB ze zálohy (lokální DB je jen pro vývoj)
```bash
docker exec -i lkkllog-dev-db-1 psql -U lkkllog -d lkkllog -q -c "DROP SCHEMA lkkl CASCADE"
docker exec -i lkkllog-dev-db-1 psql -U lkkllog -d lkkllog -q -v ON_ERROR_STOP=1 -1 \
  < /c/GIT/LKKLLog-zalohy/lkkl-RRRR-MM-DD-HHMMSS.sql > /dev/null
cd backend && uv run python -m app.migrace
```

## 4. Zkouška na kopii serveru (osobní údaje – pomocnou DB vždy smazat)
```bash
cd /c/GIT/LKKLLog/backend
F=/c/GIT/LKKLLog-zalohy/server-lkkllog-pred-NNN-$(date +%Y-%m-%d-%H%M).dump
ssh one12 'runuser -u postgres -- pg_dump -Fc lkkllog' > "$F"
D=lkkllog_kopie
docker exec lkkllog-dev-db-1 psql -U lkkllog -d postgres -q -c "DROP DATABASE IF EXISTS $D" -c "CREATE DATABASE $D"
docker exec -i lkkllog-dev-db-1 pg_restore -U lkkllog -d $D --no-owner --no-privileges < "$F"
LKKL_DATABAZE=postgresql://lkkllog:lkkllog@127.0.0.1:5432/$D uv run python -m app.migrace
docker exec lkkllog-dev-db-1 psql -U lkkllog -d $D -X -A -t -c "SELECT max(skript) FROM lkkl.migrace"  # + kontrolní dotazy převodu
docker exec lkkllog-dev-db-1 psql -U lkkllog -d postgres -q -c "DROP DATABASE $D"
```
`pg_restore` bez `--schema` (s `--schema=lkkl` se schéma nezaloží a migrace poběží nad
prázdnou DB – výsledek pak nic neříká). Výsledek převodu ověř dotazem (počty před a po).
