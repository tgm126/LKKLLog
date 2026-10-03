#!/usr/bin/env bash
# Záloha databáze přes pg_dump (nikdy nekopírovat soubory běžící databáze).
#   ./zaloha.sh                 noční záloha (cron), první den v měsíci i měsíční
#   ./zaloha.sh pred-nasazenim  záloha před nasazením nové verze
# Uchovává 14 denních, 12 měsíčních a 10 záloh před nasazením.
set -euo pipefail
cd "$(dirname "$0")"

DB=$(grep -E '^POSTGRES_DB=' .env | cut -d= -f2-)
UZIVATEL=$(grep -E '^POSTGRES_USER=' .env | cut -d= -f2-)
TED=$(date -u +%Y-%m-%d_%H%M)

if [ "${1:-}" = "pred-nasazenim" ]; then
    SLOZKA=backups/nasazeni
else
    SLOZKA=backups/denni
fi
mkdir -p backups/denni backups/mesicni backups/nasazeni

CIL="$SLOZKA/$TED.sql.gz"
docker compose exec -T db pg_dump -U "$UZIVATEL" -d "$DB" --no-owner | gzip > "$CIL.tmp"
mv "$CIL.tmp" "$CIL"

if [ -z "${1:-}" ] && [ "$(date -u +%d)" = "01" ]; then
    cp "$CIL" backups/mesicni/
fi

smaz_stare() { ls -1t "$1"/*.sql.gz 2>/dev/null | tail -n +"$(($2 + 1))" | xargs -r rm --; }
smaz_stare backups/denni 14
smaz_stare backups/mesicni 12
smaz_stare backups/nasazeni 10

echo "Záloha: $CIL ($(du -h "$CIL" | cut -f1))"
