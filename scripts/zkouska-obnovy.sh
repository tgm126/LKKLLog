#!/usr/bin/env bash
# Zkouška obnovy: stáhne poslední měsíční export ze serveru, obnoví ho do zkušební
# databáze v lokálním Dockeru (compose.dev.yaml), ověří data a databázi zase smaže.
# Spuštění z kořene repozitáře:  bash scripts/zkouska-obnovy.sh
set -euo pipefail
export MSYS_NO_PATHCONV=1  # Git Bash na Windows nesmí přepisovat cesty v kontejneru

DB_KONTEJNER=lkkllog-dev-db-1
ZKUSEBNI=obnova_test
DOCASNY=$(mktemp -d)
trap 'rm -rf "$DOCASNY"; docker exec "$DB_KONTEJNER" rm -f /tmp/zaloha.dump >/dev/null 2>&1 || true' EXIT

echo "1) Stahuji poslední export ze serveru…"
ssh one12 'cat "$(ls -1t /var/backups/lkkllog/lkkllog-*.dump | head -1)"' > "$DOCASNY/zaloha.dump"
echo "   $(wc -c < "$DOCASNY/zaloha.dump") bajtů"

echo "2) Obnovuji do zkušební databáze $ZKUSEBNI…"
zdroj="$DOCASNY/zaloha.dump"
command -v cygpath >/dev/null && zdroj=$(cygpath -w "$zdroj")  # Windows: cesta pro Docker
docker cp "$zdroj" "$DB_KONTEJNER:/tmp/zaloha.dump"
docker exec "$DB_KONTEJNER" sh -c "dropdb -U lkkllog --if-exists $ZKUSEBNI && createdb -U lkkllog $ZKUSEBNI \
    && pg_restore -U lkkllog --no-owner --no-acl -d $ZKUSEBNI /tmp/zaloha.dump"

echo "3) Ověřuji data…"
(
    cd backend
    export DATABASE_URL="postgres://lkkllog:lkkllog@127.0.0.1:5432/$ZKUSEBNI"
    chybi=$(uv run python manage.py showmigrations --plan | grep -c "\[ \]" || true)
    echo "   neaplikované migrace (export je starší než kód): $chybi"
    PYTHONIOENCODING=utf-8 uv run python manage.py shell -c "
from django.db import connection
from lety.models import AuditLog, Let, Letadlo, Uloha
from osoby.models import Osoba
print('   osoby', Osoba.objects.count(), '| letadla', Letadlo.objects.count(),
      '| úlohy', Uloha.objects.count(), '| lety', Let.objects.count(),
      '| audit', AuditLog.objects.count())
assert Osoba.objects.filter(is_superuser=True).exists(), 'chybí administrátor'
with connection.cursor() as c:
    c.execute(\"select count(*) from pg_constraint where conname = 'letadlo_bez_prekryvu'\")
    assert c.fetchone()[0] == 1, 'chybí pojistka překryvu letů'
print('   OK')
" 2>&1 | grep -v "objects imported"
)

echo "4) Mažu zkušební databázi…"
docker exec "$DB_KONTEJNER" dropdb -U lkkllog "$ZKUSEBNI"
echo "Zkouška obnovy proběhla úspěšně."
