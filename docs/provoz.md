# Provoz na serveru

Aplikace běží na `https://lety.lkkl.cz` jako **Docker aplikace ve VPS Centru**
(server `one12.vas-server.cz`, aplikace `lkkllog`, doména `lkkl.cz`).

## Jak to funguje

```
běžný commit do main  → GitHub Actions: rychlé testy backendu a frontendu (nic se nenasazuje)

značka verze (git tag v0.6.0) nebo ruční spuštění (Actions → CI → Run workflow)
  └► GitHub Actions: testy, klikací testy v prohlížeči, zkušební sestavení Docker image
     └► git push do repozitáře ve VPS Centru (f84a5@one12…/lkkllog-lkkl.cz.git),
        navíc soubor backend/VERZE s číslem verze (zobrazí se v patičce aplikace)
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
docker exec -it vpsc-app-lkkl-cz-lkkllog python /srv/lkkllog/manage.py createsuperuser
```

Logy, restart a proměnné prostředí jsou i v detailu aplikace ve VPS Centru.

> Kontejner startuje v `/app` (připojený zdrojový kód), proto se `manage.py` volá
> s plnou cestou `/srv/lkkllog/manage.py`. VPS Centrum si navíc pamatuje proměnné
> prostředí z prvního image – aplikace proto na proměnné z `Dockerfile` nespoléhá.

## Firewall a SSH

SSH je na serveru povolené jen z vybraných zemí (GeoIP). Kvůli nasazování z GitHub
Actions je povolené i USA. fail2ban banuje IP adresy po několika rychlých spojeních
za sebou (např. `ssh-keyscan`); odblokování: VPS Centrum → Zabezpečení → fail2ban.

## E-mail

- Aplikace odesílá přes schránku `info@lkkl.cz` na tomto serveru (SMTP `one12.vas-server.cz:465`).
  Přístup je v Env proměnných aplikace: `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, k tomu `APP_URL=https://lety.lkkl.cz` pro odkazy v e-mailech.
- Heslo schránky jen z písmen a číslic (zvláštní znaky v proměnných prostředí dělaly potíže).
- Co se smí odeslat, řídí **Administrace → Nastavení provozu → režim odesílání e-mailů**.
- Vnitřní síť Dockeru `172.17.0.0/16` je ve fail2ban mezi ignorovanými adresami. Bez toho
  stačí pár neúspěšných přihlášení k poště a fail2ban zablokuje samotnou aplikaci.

## Údržba (cron)

Systémový cron serveru (`/etc/cron.d/lkkllog`), protože cron ve VPS Centru běží pod
uživatelem domény bez práv k Dockeru. Skript je v repozitáři `server/udrzba.sh`, na
serveru v `/usr/local/lib/lkkllog/udrzba.sh`. Při úspěchu nic nehlásí, chyby chodí e-mailem.

| Kdy (čas serveru) | Úloha |
|---|---|
| denně 3:17 | `prihlaseni` – smaže prošlá přihlášení (`clearsessions`) |
| neděle 3:27 | `docker-uklid` – mezipaměť sestavení Dockeru zmenší na 1 GB |
| pondělí 3:37 | `export` – `pg_dump` do `/var/backups/lkkllog` (posledních 52), kopie e-mailem administrátorům |
| denně 5:00 | `uzaverka` – automatická uzávěrka předchozích dnů (viz návrh kap. 4.7) |
| každých 5 min, 6–22 h | `upozorneni` – upozornění na neukončené lety e-mailem a push (viz návrh kap. 4.9a) |

Instalace / aktualizace (z počítače správce):

```bash
tar -C server -cf - udrzba.sh cron.lkkllog | ssh one12 'cd /tmp && tar -xf - && install -D -m 755 udrzba.sh /usr/local/lib/lkkllog/udrzba.sh && install -m 644 cron.lkkllog /etc/cron.d/lkkllog && rm udrzba.sh cron.lkkllog'
```

Obnova z exportu: `pg_restore --clean --if-exists -d lkkllog lkkllog-RRRR-MM-DD.dump`
(jako uživatel `postgres`). Export neobsahuje přihlášení (sessions), ostatní data ano.

## Hlídání dostupnosti

GitHub Actions (`.github/workflows/dostupnost.yml`) se každé 2 hodiny přes den (7–21 h letního času, 6–20 h zimního; nikdy mezi 23 a 6 h) zeptá
`https://lety.lkkl.cz/api/health`. Když aplikace neodpoví, běh selže a GitHub pošle e-mail.
Častější kontrola by v soukromém repozitáři zbytečně spotřebovávala bezplatné minuty GitHub Actions.

## Zálohy a obnova

**Co se zálohuje:**

| Záloha | Kde | Jak dlouho |
|---|---|---|
| Zálohy hostingu (databáze `lkkllog`) | VPS Centrum → Zálohování, úložiště **„Lokální disk“** serveru; zda je hosting kopíruje i mimo server, je potřeba ověřit | denní 7 dní, týdenní 30 dní |
| Týdenní export databáze (`pg_dump`) | `/var/backups/lkkllog` na serveru + e-mail administrátorům (Gmail = kopie mimo server) | 52 týdnů na serveru, v e-mailu trvale |

Zálohy hostingu (zjištěno 4. 10. 2026): plánovač VPS Centra zálohuje každou databázi
denně ve 4:00 času serveru; v neděli jako *weekly*, ostatní dny *daily*. Ukládá je jako
ZIP do `/root/backup/domains/<doména>/databases/<databáze>/` na **stejném disku**.
Denní drží zhruba týden, týdenní 30 dní – k dispozici je tedy každý den posledního týdne
a každá neděle posledního měsíce. Mimo server je jen náš týdenní export v e-mailu.

Kód zálohovat netřeba (je na GitHubu), Docker image se z kódu sestaví znovu.
Tajné údaje v Env proměnných aplikace nejsou nenahraditelné: nový `DJANGO_SECRET_KEY`
jen odhlásí všechny uživatele a zneplatní rozeslané odkazy na nastavení hesla,
heslo ke schránce jde ve VPS Centru nastavit znovu.

**Zkouška obnovy** (doporučeno jednou za čtvrtletí, z počítače správce, běžící
`compose.dev.yaml`): `bash scripts/zkouska-obnovy.sh` – stáhne poslední týdenní export, obnoví ho
do zkušební databáze, ověří data a databázi smaže. První zkouška 4. 10. 2026: v pořádku.

**Postup při problému** (vždy nejdřív zastavit aplikaci ve VPS Centru, ať se mezitím nic nezapisuje):

1. *Chybná data z posledních 30 dní:* VPS Centrum → Zálohování → obnovit databázi
   `lkkllog` k vybranému dni. Pozor, přepíše celou databázi – změny od zálohy se ztratí.
   Když jde jen o pár záznamů, je lepší obnovit zálohu do jiné databáze a záznamy
   přenést ručně.
2. *Starší data:* z týdenního exportu na serveru nebo z e-mailu (jako `postgres`):
   `pg_restore --clean --if-exists -d lkkllog /var/backups/lkkllog/lkkllog-RRRR-MM-DD.dump`
3. *Ztráta celého serveru:* nový server s Dockerem → ve VPS Centru PostgreSQL databáze
   `lkkllog` → `pg_restore` posledního exportu (nebo zálohy hostingu) → Docker aplikace
   podle začátku tohoto dokumentu (ZIP z GitHubu, Dockerfile, port 8000, Env proměnné,
   databáze, subdoména `lety`) → SSH klíč pro GitHub Actions u uživatele VPS Centra.
