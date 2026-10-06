# LKKL Log – pokyny pro vývoj

> **NÁVRH k odsouhlasení.** Uživatel instrukce prochází; body označené *k projednání*
> zatím neplatí. Po odsouhlasení tuto poznámku smazat.

Evidence letů aeroklubu Kladno (LKKL). Od 5. 10. 2026 se staví **znovu od začátku** – čistý
stůl, nic se nepřebírá automaticky. Stará verze je ve větvi `v1` (ke čtení ve složce
`C:\GIT\LKKLLog-v1`); slouží jen jako zdroj znalostí, ne jako základ kódu. Podklady:
`docs/podklady/` (doménová pravidla, předpisy, server, poznatky z první verze).

## Spolupráce
- Komunikace česky; odborné výrazy vysvětlit jednou větou.
- **Co uživatel řekne, není zákon.** Když vidím riziko nebo lepší řešení, předložím ho
  k diskusi s doporučením, než začnu realizovat.
- Uživatel je databázista: datový model předkládat v databázových pojmech (tabulky, klíče,
  omezení, DDL, pohledy).
- Na kódu pracujeme jen my dva.

## Postup
1. **Nejdřív návrh, pak kód.** Každý modul začne krátkým dokumentem v `docs/` (data,
   obrazovky, pravidla); kód až po schválení.
2. **Malé moduly dotažené do konce** (testy, dokumentace, vyzkoušeno na mobilu i desktopu),
   než se začne další. Nic se nestaví „do zásoby“.
3. **Žádné záplaty.** Při změně požadavku se nejdřív upraví návrh, pak se kód přepíše, jako by
   to tak bylo od začátku; starý kód se úplně smaže (žádné vrstvy kompatibility ani dočasné
   obezličky).
4. **Slepé uličky** se zkoušejí na odbočce (větvi); když se nepovedou, odbočka se zahodí.
5. **Data zadává uživatel** (číselníky, osoby, letadla…) a **mění je i přímo v databázi**.
   Pravdou o datech je databáze, ne skripty: nikdy schéma nezakládat znovu ani data
   nepřepisovat. Změny struktury jen novým skriptem (`ALTER`…), který data zachová.
   Skripty `_data.sql` jsou jen počáteční naplnění; na server se data přenesou výpisem
   z lokální databáze. Žádné importy z Excelu.
   Před každou změnou struktury udělat zálohu: `bash db/zaloha.sh` (do
   `C:\GIT\LKKLLog-zalohy`, mimo git – budou tam i osobní údaje).
6. Skripty v `db/` se před první migrací na server mohou sloučit do čistého celku (data
   se přitom vezmou z databáze).
7. **Tabulky:** stará verze je zinventarizovaná v `docs/tabulky-v1.md` (po spuštění nové
   verze se smažou), nová se vede v `docs/tabulky.md`.

## Datový model
8. **Normální formy:** každý údaj uložený jednou; odvozené hodnoty generovaným sloupcem
   nebo pohledem (view), ne kopií.
9. **Klíče a omezení:** umělý primární klíč + jedinečné přirozené klíče; cizí klíče všude bez
   kaskádového mazání; pravidla v databázi (CHECK, UNIQUE, EXCLUDE).
10. **Auditní log triggerem v databázi** (zachytí i přímou opravu v databázi).
    **Standard číselníku `lov_*`:** `id` (vazby mezi tabulkami **vždy přes id**), `kod`
    (jedinečný, jen pro program, nikde se nezobrazuje), `nazev` (text pro zobrazení – jde měnit
    a nemusí být jedinečný), `poradi`, `platny` (přepínač „používat“; nemaže se, zneplatní se;
    nepoužitou položku jde smazat; **nabídky** aplikace bere vždy z pohledu `v_lov_<název>`
    s platnými položkami seřazenými podle pořadí – každý číselník ho má). Pravidla sloupců jsou v doménách `lkkl.kod`, `lkkl.nazev`,
    `lkkl.poradi`, `lkkl.platny` – definovaná jednou. Hodnoty, podle jejichž kódu program
    uplatňuje pravidla, patří do skriptu struktury (ne do `_data.sql`).
11. Časy v UTC. Doménové názvy česky bez diakritiky, technické anglicky.
    **Nové tabulky ve schématu databáze `lkkl`**; staré tabulky
    první verze zůstávají ve schématu `public`, dokud je nesmažeme.
12. **Zdrojem pravdy o schématu jsou SQL skripty** v `db/`, číslované `NNN_nazev.sql` (DDL)
    a `NNN_nazev_data.sql` (data zadaná uživatelem). Vznikají a zkouší se v lokální databázi
    (Docker, `127.0.0.1:5432`, databáze `lkkllog`), na server se zmigrují později.
    Předpony: `lov_` číselníky, `v_` pohledy. Seznam objektů v `docs/tabulky.md`.

## Technologie
- **Databáze:** PostgreSQL, schéma `lkkl` (viz výše).
- **Server:** Python + **FastAPI**, dotazy **přímo v SQL** (psycopg) nad tabulkami a pohledy –
  žádné ORM ani tabulky frameworku, schéma se nepopisuje podruhé v Pythonu. Přihlašování,
  relace, ochrana formulářů a omezení pokusů jsou vlastní (tabulky `ucet`, `relace`), pokryté
  testy. Hesla argon2id.
- Přihlášení e-mailem a heslem, platí 30 dní od poslední aktivity; admin se smí přihlásit
  jako jiná osoba (relace si pamatuje skutečného admina). Passkey zatím ne.

## Příkazy (ve složce `backend/`)
- Server pro vývoj: `uv run uvicorn app.main:app --reload` → rozhraní na
  `http://localhost:8000/api/docs`.
- **Před commitem:** `uv run ruff check . && uv run ruff format --check . && uv run pytest`.
  Testy si samy sestaví databázi `lkkllog_test` ze skriptů `db/` (bez `_data`) – data
  uživatele v `lkkllog` nikdy nepoužívají.
- Odkaz pro nastavení hesla: `uv run python -m app.prikazy odkaz <e-mail>`; úklid prošlých
  relací: `uv run python -m app.prikazy uklid`.

## Obrazovky
13. **Samostatný design pro mobil a pro desktop** – ne jedna stránka, která se jen roztáhne.
    Každá obrazovka má návrh pro telefon (od šířky 375 px, ovládání palcem) i pro velkou
    obrazovku (víc informací najednou).
14. **Jednotný vizuální systém** definovaný dřív než první obrazovka: **tři velikosti písma**
    (12 / 15 / 20 px), bezpatkové; pevná sada mezer; barvy jen pro význam; štítky (badge);
    lety jako zaoblené pásky (připomínají stripy ŘLP); světlý i tmavý režim s přepínačem
    v aplikaci (podle zařízení / světlý / tmavý); hustě, ale čitelně. Maketa:
    `docs/navrhy/lety-mobil.html`.
    **Normalizace stylů – každá vlastnost definovaná právě jednou:**
    - **Tokeny** na jednom místě: barvy (každá se světlou i tmavou hodnotou v jedné definici,
      `light-dark()`), velikosti a tloušťky písma, stupnice mezer, zaoblení, rámeček, rozměry
      dotykových prvků. Jinde žádná pevná barva ani rozměr.
    - **Komponenty** (pásek letu, štítek, tlačítko, nadpis sekce…) definované jednou, složené
      jen z tokenů. **Varianty** mění jen to, čím se liší (typicky přes vlastní proměnnou
      komponenty), žádné přepisování přepsaného ani vložené styly v HTML.
    - **Výjimka** je možná jen se zdůvodněním přímo u ní: komentář `VÝJIMKA: důvod`.
    - V aplikaci to hlídá kontrola stylů (stylelint) před commitem: pevná barva nebo rozměr
      mimo soubor s tokeny neprojde.
15. Žádná vestavěná administrace frameworku; všechno, co admin dělá, je v aplikaci.
    Nouzové opravy přímo v databázi.

## Testování
16. Každá funkce prochází **třemi fázemi**:
    1. **testuje jen uživatel** (správce projektu);
    2. **testují vybraní pilotní uživatelé**;
    3. **rollout na všechny**.
    *K projednání:* jak fáze technicky oddělit (prostředí, adresa, přístup) a zda se postupuje
    po modulech, nebo za celou aplikaci. Automatické testy u mě běží při každé změně.

## K projednání (převzato z první verze, zatím neplatí)
Projdeme jednotlivě, aby se nezanesl starý problém:
- oprávnění kontrolovat na serveru, ne jen ve frontendu;
- žádné e-maily členům před spuštěním; pozvánky jen ruční akcí admina;
- telefon osoby jen na vyžádání;
- hesla a klíče mimo git (proměnné prostředí);
- na server jedno SSH spojení (`ssh one12`, fail2ban banuje rychlá opakovaná spojení);
- nasazení jen značkou verze – pozor: archivní značky nesmí odpovídat vzoru nasazovacích;
- soubory uživatele nepřepisovat ani nemazat (nové verze pod novým jménem);
- frontend (React?) a hosting (Docker ve VPS Centru).

## Stav
- Server `https://lety.lkkl.cz` dál provozuje první verzi (větev `v1`). Případná oprava staré
  verze se dělá ve větvi `v1` a nasazuje značkou `v0.14.x` jako dosud.
- Hlavní větev zatím nemá nasazovací workflow – nic se z ní nenasazuje.
