#!/usr/bin/env bash
# Údržba aplikace LKKL Log na serveru one12 (spouští ji cron, viz server/cron.lkkllog).
# Při úspěchu nic nevypisuje; cokoli na výstupu pošle cron e-mailem adminovi.
#   udrzba.sh prihlaseni    smaže prošlá přihlášení (denně)
#   udrzba.sh docker-uklid  zmenší mezipaměť sestavení Dockeru na 1 GB (týdně)
#   udrzba.sh export        export databáze, uchová 52 posledních, pošle e-mailem (týdně)
#   udrzba.sh uzaverka      automatická denní uzávěrka po soumraku (každých 15 minut)
set -euo pipefail

KONTEJNER=vpsc-app-lkkl-cz-lkkllog
ZALOHY=/var/backups/lkkllog

case "${1:-}" in
prihlaseni)
    docker exec "$KONTEJNER" python /srv/lkkllog/manage.py clearsessions
    ;;
docker-uklid)
    docker builder prune --force --keep-storage 1GB >/dev/null
    ;;
export)
    install -d -m 700 "$ZALOHY"
    soubor="$ZALOHY/lkkllog-$(date +%Y-%m-%d).dump"
    # Formát pg_dump „custom“ je komprimovaný; přihlášení (sessions) nejsou potřeba.
    runuser -u postgres -- pg_dump --format=custom --exclude-table-data=django_session \
        lkkllog > "$soubor.tmp"
    mv "$soubor.tmp" "$soubor"
    chmod 600 "$soubor"
    ls -1t "$ZALOHY"/lkkllog-*.dump | tail -n +53 | xargs -r rm --
    docker exec -i "$KONTEJNER" python /srv/lkkllog/manage.py odeslat_zalohu \
        --nazev "$(basename "$soubor")" < "$soubor" >/dev/null
    ;;
uzaverka)
    docker exec "$KONTEJNER" python /srv/lkkllog/manage.py automaticka_uzaverka
    ;;
*)
    echo "Použití: $0 prihlaseni|docker-uklid|export|uzaverka" >&2
    exit 2
    ;;
esac
