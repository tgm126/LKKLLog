#!/usr/bin/env bash
# Záloha schématu lkkl z lokální databáze (Docker) do složky mimo git.
#   bash db/zaloha.sh
# Obnova do prázdné databáze (schéma lkkl nesmí existovat):
#   docker exec -i lkkllog-dev-db-1 psql -U lkkllog -d lkkllog -v ON_ERROR_STOP=1 -1 < soubor.sql
set -euo pipefail

CIL="${LKKL_ZALOHY:-/c/GIT/LKKLLog-zalohy}"
mkdir -p "$CIL"
soubor="$CIL/lkkl-$(date +%Y-%m-%d-%H%M%S).sql"

docker exec lkkllog-dev-db-1 pg_dump -U lkkllog -d lkkllog \
    --schema=lkkl --no-owner --no-privileges > "$soubor"

echo "Záloha: $soubor ($(wc -c < "$soubor") B)"
