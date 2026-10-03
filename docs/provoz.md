# Provoz na serveru

Aplikace běží na `https://lety.lkkl.cz` jako **Docker aplikace ve VPS Centru**
(server `one12.vas-server.cz`, aplikace `lkkllog`, doména `lkkl.cz`).

## Jak to funguje

```
push do main na GitHubu
  └► GitHub Actions: testy backendu a frontendu, zkušební sestavení Docker image
     └► git push do repozitáře ve VPS Centru (f84a5@one12…/lkkllog-lkkl.cz.git)
        └► VPS Centrum: rozbalí kód do /www/hosting/lkkl.cz/.apps/lkkllog,
           sestaví image z Dockerfile a restartuje kontejner
           └► při startu kontejneru proběhnou migrace (DJANGO_MIGRATE_ON_START=1)
```

- **Proxy, HTTPS a přesměrování na HTTPS** nastavuje VPS Centrum (port v kontejneru 8000).
- **Databáze** je PostgreSQL serveru (`lkkllog`), přiřazená ve VPS Centru. Do kontejneru
  přijde jako `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_SOCKET` (unixový socket).
- **Zálohy databáze** dělá Váš Hosting (denní 7 dní, týdenní 30 dní, mimo server).
- **Proměnné prostředí** (tajný klíč aplikace, povolené adresy) se nastavují ve VPS Centru
  v detailu aplikace → Env proměnné. Do gitu nepatří.
- Limit paměti kontejneru: 512 MB.

## Důležité vlastnosti VPS Centra

- Zdrojový kód je v kontejneru připojený na `/app`, proto aplikace v image leží
  v `/srv/lkkllog` (jinak by ji připojená složka překryla).
- Kontejner běží pod uživatelem domény (`lkkl-cz`), ne pod rootem.
- nginx blokuje cesty a subdomény `config|tmp|temp|log|logs|bin|inc` (vrací 403).

## Přístupy

| Co | Kde |
|---|---|
| SSH na server (root) | klíč `~/.ssh/one12_ed25519` na počítači správce, `ssh one12` |
| Push do VPS Centra | klíč `github-actions-lkkllog` u uživatele VPS Centra, soukromá část v GitHub secret `VPSC_SSH_KEY` |

## Užitečné příkazy (na serveru jako root)

```bash
docker ps --filter name=vpsc-app-lkkl-cz-lkkllog
docker logs --tail 100 vpsc-app-lkkl-cz-lkkllog
docker exec -it vpsc-app-lkkl-cz-lkkllog python manage.py createsuperuser
```

Logy, restart a proměnné prostředí jsou i v detailu aplikace ve VPS Centru.
