# Příprava serveru (jednorázově)

Server `one12.vas-server.cz`, aplikace ve složce `/opt/lkkllog`, běží pod uživatelem
`lkkllog`. Příkazy se spouštějí jako `root`.

## 1. Uživatel a složka

```bash
useradd --create-home --shell /bin/bash lkkllog
usermod -aG docker lkkllog
mkdir -p /opt/lkkllog
chown lkkllog:lkkllog /opt/lkkllog
```

## 2. Soubory aplikace

Do `/opt/lkkllog` nahrát z repozitáře: `compose.yaml`, `deploy/deploy.sh`,
`deploy/zaloha.sh`, `deploy/udrzba.sh` (skripty přímo do `/opt/lkkllog`, ne do podsložky)
a vytvořit `.env` podle `.env.example`:

```bash
cd /opt/lkkllog
chmod +x deploy.sh zaloha.sh udrzba.sh
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # POSTGRES_PASSWORD
nano .env
chmod 600 .env
chown -R lkkllog:lkkllog /opt/lkkllog
```

V `.env` je potřeba `APP_IMAGE=ghcr.io/tgm126/lkkllog:latest` (první nasazení ho přepíše
na konkrétní verzi).

## 3. SSH klíč pro GitHub Actions

Klíč smí spustit **jen** `deploy.sh` (nic jiného na serveru neudělá):

```bash
mkdir -p /home/lkkllog/.ssh
echo 'command="/opt/lkkllog/deploy.sh",no-port-forwarding,no-agent-forwarding,no-X11-forwarding,no-pty ssh-ed25519 AAAA... github-actions-lkkllog' \
    >> /home/lkkllog/.ssh/authorized_keys
chown -R lkkllog:lkkllog /home/lkkllog/.ssh
chmod 700 /home/lkkllog/.ssh && chmod 600 /home/lkkllog/.ssh/authorized_keys
```

Na GitHubu (Settings → Secrets and variables → Actions):

| Typ | Název | Hodnota |
|---|---|---|
| Secret | `DEPLOY_SSH_KEY` | soukromý klíč k veřejnému klíči výše |
| Secret | `DEPLOY_KNOWN_HOSTS` | výstup `ssh-keyscan one12.vas-server.cz` |
| Variable | `DEPLOY_HOST` | `one12.vas-server.cz` |
| Variable | `DEPLOY_ENABLED` | `true` (zapne automatické nasazování) |

## 4. Cron (uživatel `lkkllog`)

```
0 2 * * *  /opt/lkkllog/zaloha.sh
0 3 * * 0  /opt/lkkllog/udrzba.sh
```

## 5. nginx

Subdoména `lety.lkkl.cz` musí předávat požadavky na `http://127.0.0.1:8000` a posílat
hlavičky `Host`, `X-Forwarded-For` a `X-Forwarded-Proto`.

## Ruční příkazy

```bash
cd /opt/lkkllog
docker compose ps                     # stav
docker compose logs -f web            # logy aplikace
docker compose exec web python manage.py createsuperuser
./zaloha.sh                           # ruční záloha
```

Návrat k předchozí verzi: hodnotu z `.predchozi_image` vložit do `APP_IMAGE` v `.env`
a spustit `docker compose up -d web`.
