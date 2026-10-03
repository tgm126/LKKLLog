#!/bin/sh
# Start kontejneru: volitelně nejdřív migrace databáze, pak samotná aplikace.
set -e
if [ "${DJANGO_MIGRATE_ON_START:-0}" = "1" ]; then
    python manage.py migrate --noinput
fi
exec "$@"
