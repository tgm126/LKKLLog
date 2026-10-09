#!/usr/bin/env bash
# Aktuální schéma lkkl jako jeden čitelný soubor docs/schema.sql (code review 9. 10. 2026, D4):
# definice tabulek, pohledů, funkcí a triggerů jsou jinak jen rozprostřené po desítkách skriptů
# db/ (let_zkontrolovat má sedm verzí, v_let devět). Soubor se generuje – neupravuje ručně:
# pomocná databáze lkkllog_schema se sestaví spouštěčem migrací ze skriptů db/ a vypíše se
# pg_dump; CI hlídá, že docs/schema.sql odpovídá skriptům (git diff). Spustit po každém novém
# skriptu db/:
#   bash db/schema.sh
# Databáze v Dockeru (lokálně lkkllog-dev-db-1; v CI id kontejneru služby postgres):
#   LKKL_DB_KONTEJNER=... bash db/schema.sh
set -euo pipefail

KONTEJNER="${LKKL_DB_KONTEJNER:-lkkllog-dev-db-1}"
DB=lkkllog_schema
cd "$(dirname "$0")/.."

docker exec "$KONTEJNER" psql -U lkkllog -d postgres -q \
    -c "DROP DATABASE IF EXISTS $DB" -c "CREATE DATABASE $DB"
(cd backend && LKKL_DATABAZE="postgresql://lkkllog:lkkllog@127.0.0.1:5432/$DB" \
    uv run python -m app.migrace > /dev/null)
{
    echo "-- Aktuální schéma lkkl: generuje bash db/schema.sh ze skriptů db/ – neupravovat ručně."
    echo "-- Zdrojem pravdy zůstávají skripty db/ (CLAUDE.md 12); tohle je jejich výsledek v jednom souboru."
    # bez řádků, které se liší spuštění od spuštění (verze, náhodný klíč \restrict)
    docker exec "$KONTEJNER" pg_dump -U lkkllog -d "$DB" \
        --schema-only --schema=lkkl --no-owner --no-privileges \
        | grep -v -E '^(-- Dumped (from|by) |\\(un)?restrict )'
} > docs/schema.sql
docker exec "$KONTEJNER" psql -U lkkllog -d postgres -q -c "DROP DATABASE $DB"

echo "docs/schema.sql: $(wc -l < docs/schema.sql) řádků"
