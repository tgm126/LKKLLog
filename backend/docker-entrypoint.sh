#!/bin/sh
# Start kontejneru: volitelně nejdřív migrace databáze, pak samotná aplikace.
set -e
# VPS Centrum spouští kontejner v /app (připojený zdrojový kód) – aplikace je v /srv/lkkllog.
cd /srv/lkkllog
if [ "${DJANGO_MIGRATE_ON_START:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi
exec "$@"
