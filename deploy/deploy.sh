#!/usr/bin/env bash
# Nasazení nové verze aplikace. Spouští ho GitHub Actions přes SSH:
#   echo "$GITHUB_TOKEN" | ssh lkkllog@server <commit-sha>
# SSH klíč GitHubu smí spustit jen tento skript (forced command v authorized_keys),
# verze přijde v SSH_ORIGINAL_COMMAND, dočasný token pro GHCR na standardním vstupu.
set -euo pipefail
cd "$(dirname "$0")"

TAG="${1:-${SSH_ORIGINAL_COMMAND:-}}"
if [[ ! "$TAG" =~ ^[0-9a-f]{40}$ ]]; then
    echo "Neplatná verze: '$TAG'" >&2
    exit 2
fi

REPO=ghcr.io/tgm126/lkkllog
NOVY="$REPO:$TAG"
STARY=$(grep -E '^APP_IMAGE=' .env | cut -d= -f2-)
APP_PORT=$(grep -E '^APP_PORT=' .env | cut -d= -f2-)

log() { echo "[$(date -u +%FT%TZ)] $*"; }
nastav_image() { sed -i "s#^APP_IMAGE=.*#APP_IMAGE=$1#" .env; }
zdrava() { curl -fsS --max-time 3 "http://127.0.0.1:${APP_PORT}/api/health" | grep -q '"status": *"ok"'; }

if [ ! -t 0 ]; then
    token=$(cat)
    if [ -n "$token" ]; then
        echo "$token" | docker login ghcr.io -u github --password-stdin >/dev/null
        trap 'docker logout ghcr.io >/dev/null 2>&1 || true' EXIT
    fi
fi

log "Spouštím databázi"
docker compose up -d --wait db

log "Záloha databáze před nasazením"
./zaloha.sh pred-nasazenim

log "Stahuji $NOVY"
docker pull "$NOVY"
nastav_image "$NOVY"

log "Migrace databáze"
if ! docker compose run --rm web python manage.py migrate --noinput; then
    log "Migrace selhala – ponechávám předchozí verzi $STARY"
    nastav_image "$STARY"
    exit 1
fi

log "Restartuji aplikaci"
docker compose up -d web
for _ in $(seq 1 30); do
    if zdrava; then
        echo "$STARY" > .predchozi_image
        log "Nasazeno: $TAG"
        exit 0
    fi
    sleep 2
done

log "Aplikace neodpovídá – vracím předchozí verzi $STARY"
nastav_image "$STARY"
docker compose up -d web
exit 1
