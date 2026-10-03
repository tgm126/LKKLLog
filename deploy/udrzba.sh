#!/usr/bin/env bash
# Týdenní údržba (cron): smaže nepoužívané Docker image a mezipaměť sestavení
# starší 14 dnů a upozorní na docházející místo na disku.
# Smazané verze aplikace zůstávají v GHCR, návrat k nim tedy funguje dál.
set -euo pipefail

docker image prune -af --filter "until=336h"
docker builder prune -f --filter "until=336h"

POUZITO=$(df --output=pcent / | tail -1 | tr -dc '0-9')
if [ "$POUZITO" -ge 85 ]; then
    # Výstup cronu chodí e-mailem správci.
    echo "POZOR: disk serveru je zaplněný na $POUZITO %." >&2
    exit 1
fi
