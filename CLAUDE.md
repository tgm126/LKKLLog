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
   než se začne další. Nic se nestaví „do zásoby“. K dokumentaci patří **příručka pro
   uživatele** `docs/prirucka.md` (krátká, podle situací, ne podle tlačítek): každou změnu
   chování, kterou uživatel aplikace pozná, do ní promítnout ve stejném commitu.
3. **Žádné záplaty.** Při změně požadavku se nejdřív upraví návrh, pak se kód přepíše, jako by
   to tak bylo od začátku; starý kód se úplně smaže (žádné vrstvy kompatibility ani dočasné
   obezličky).
4. **Slepé uličky** se zkoušejí na odbočce (větvi); když se nepovedou, odbočka se zahodí.
   **Technický dluh** (co by šlo lépe, ale odkládá se na další zásah do souboru) se vede
   v `docs/dluh.md`; před úpravou souboru se tam podívat, vyřešené položky mazat.
5. **Data zadává uživatel** (číselníky, osoby, letadla…) a **mění je i přímo v databázi**.
   **Pravdou o datech je serverová databáze** (od 6. 10. 2026; ruční úpravy přes správce
   databází ve VPS Centru). Lokální databáze je jen pro testy a vývoj změn datového modelu.
   Nikdy schéma nezakládat znovu ani data nepřepisovat. Změny struktury jen novým skriptem
   (`ALTER`…), který data zachová; na server je doveze spouštěč migrací při nasazení.
   Skripty `_data.sql` (019, 021, 041) jsou počáteční naplnění číselníků; nová lokální
   databáze vzniká obnovou zálohy serveru, ne z nich. Každý `_data` skript musí používat
   příprava klikacích testů (`backend/tests/e2e_priprava.py`) – jinak zastará bez povšimnutí
   (letadla a letiště 001/003 tak dopadly a 9. 10. 2026 byly smazány). Žádné importy z Excelu.
   Před každou změnou struktury udělat zálohu: `bash db/zaloha.sh` (do
   `C:\GIT\LKKLLog-zalohy`, mimo git – budou tam i osobní údaje).
6. Skripty v `db/` se před první migrací na server mohou sloučit do čistého celku (data
   se přitom vezmou z databáze).
7. **Tabulky:** seznam se vede v `docs/tabulky.md` (`docs/tabulky-v1.md` je jen podklad –
   tabulky první verze jsou smazané).

## Datový model
8. **Normální formy:** každý údaj uložený jednou; odvozené hodnoty generovaným sloupcem
   nebo pohledem (view), ne kopií.
9. **Klíče a omezení:** umělý primární klíč + jedinečné přirozené klíče; cizí klíče všude bez
   kaskádového mazání; pravidla v databázi (CHECK, UNIQUE, EXCLUDE).
10. **Auditní log triggerem v databázi** (zachytí i přímou opravu v databázi).
    **Předpona `lov_` = trvalá data** (číselníky, osoby, letadla, osnovy, popisky auditu
    i vazební tabulky mezi nimi); ostatní tabulky jsou provozní data (lety, audit, relace)
    a technické (`ucet`, `migrace`, `nastaveni`).
    **Standard jednoduchého číselníku:** `id` (vazby mezi tabulkami **vždy přes id**), `kod`
    (jedinečný, jen pro program, nikde se nezobrazuje), `nazev` (text pro zobrazení – jde měnit
    a nemusí být jedinečný), `poradi`, `platny` (přepínač „používat“; nemaže se, zneplatní se;
    nepoužitou položku jde smazat; **nabídky** aplikace bere vždy z pohledu `v_lov_<název>`
    s platnými položkami seřazenými podle pořadí). Pravidla sloupců jsou v doménách `lkkl.kod`, `lkkl.nazev`,
    `lkkl.poradi`, `lkkl.platny` – definovaná jednou. Hodnoty, podle jejichž kódu program
    uplatňuje pravidla, patří do skriptu struktury (ne do `_data.sql`).
    **Dva druhy `kod`** (rozhodnuto 9. 10. 2026): **řídicí číselníky** (účel, funkce, způsob
    vzletu, kategorie…) – `kod` je jen pro program a nezobrazuje se; **evidenční číselníky
    s oficiálním označením** (osnova `IU`, úloha `8P` v rámci osnovy, typ přezkoušení `PC-SEP`) – `kod` je to označení
    a zobrazuje se. Označení se v názvu neopakuje (osnova `IU` / „Výcvik SPL…“); složený text
    pro aplikaci („IU – Výcvik SPL…“, „IU/8P Přezkoušení…“) skládá pohled.
    **Platnost záznamu** (od 8. 10. 2026, skript 031): **každá tabulka `lov_` s vlastním `id`**
    (číselníky i osoby, letadla) má sloupec `platny lkkl.platny`. Neplatný záznam zůstává
    jen kvůli starým vazbám: **nikde se nenabízí** (pohledy `v_lov_*`, správa osob ukazuje
    i neplatné, aby šly vrátit) a **nejde nově použít** – hlídá trigger
    `kontrola_platnosti` na každém cizím klíči do `lov_` (stará vazba při úpravě jiného
    údaje projde). Platnost se nedědí. Bez platnosti jsou vazební tabulky a `lov_audit_popisek`.
    Nová tabulka `lov_` = sloupec `platny`, pohled `v_lov_…` a triggery na vazby do ní.
11. Časy v UTC. Doménové názvy česky bez diakritiky, technické anglicky.
    **Tabulky ve schématu databáze `lkkl`**; tabulky první verze byly 6. 10. 2026 smazány
    (ve `public` zůstává jen rozšíření `btree_gist`).
12. **Zdrojem pravdy o schématu jsou SQL skripty** v `db/`, číslované `NNN_nazev.sql` (DDL)
    a `NNN_nazev_data.sql` (data zadaná uživatelem; tabulku `lkkl.migrace` zakládá spouštěč
    sám – musí existovat dřív než první skript). Vznikají a zkouší se v lokální databázi
    (Docker, `127.0.0.1:5432`, databáze `lkkllog`), na server se zmigrují později.
    Předpony: `lov_` číselníky, `v_` pohledy. Seznam objektů v `docs/tabulky.md`; **aktuální
    schéma v jednom souboru** `docs/schema.sql` (generuje `bash db/schema.sh` ze skriptů,
    po každém novém skriptu přegenerovat – CI hlídá shodu; neupravovat ručně).

## Technologie
- **Databáze:** PostgreSQL, schéma `lkkl` (viz výše).
- **Server:** Python + **FastAPI**, dotazy **přímo v SQL** (psycopg) nad tabulkami a pohledy –
  žádné ORM ani tabulky frameworku, schéma se nepopisuje podruhé v Pythonu. Přihlašování,
  relace, ochrana formulářů a omezení pokusů jsou vlastní (tabulky `ucet`, `relace`), pokryté
  testy. Hesla argon2id.
- **Audit:** každý požadavek nastaví databázi, kdo jedná (`db.s_kontextem` / `nastavit_kontext`);
  zapisuje trigger v databázi, čitelně pohledy `v_audit` a `v_historie_letu`.
- Přihlášení e-mailem a heslem, platí 30 dní od poslední aktivity; admin se smí přihlásit
  jako jiná osoba (relace si pamatuje skutečného admina). Passkey zatím ne.
- **Rozhraní popsané jednou:** každý endpoint má `response_model` (modely dědí z `app/model.py`
  `Model`, dokumentační řetězce položek jdou do OpenAPI). Typy pro frontend se **generují**
  (`npm run api-typy` → `frontend/src/api.gen.ts`, součást `npm run kontrola`; CI hlídá, že
  soubor odpovídá serveru) – v `*/api.ts` jsou jen aliasy `Schemata["…"]`, ručně se typy
  odpovědí nepíší.

## Příkazy (ve složce `backend/`, frontend ve složce `frontend/`)
- Server pro vývoj: `uv run uvicorn app.main:app --reload` → rozhraní na
  `http://localhost:8000/api/docs`. Frontend pro vývoj: `npm run dev` → obrazovky na
  `http://localhost:5173` (rozhraní `/api` přeposílá serveru).
- **Před commitem:** `uv run ruff check . && uv run ruff format --check . && uv run pytest`,
  ve `frontend/` `npm run kontrola` (typy, eslint, stylelint) a `npm run e2e` (sestavení
  a klikací testy v rozměru mobilu). Testy si samy sestaví databáze `lkkllog_test`
  a `lkkllog_e2e` ze skriptů `db/` (bez `_data`) – data uživatele v `lkkllog` nikdy nepoužívají.
- Odkaz pro nastavení hesla: `uv run python -m app.prikazy odkaz <e-mail>`; úklid prošlých
  relací: `uv run python -m app.prikazy uklid`.
- **Migrace:** `uv run python -m app.migrace` provede nové skripty `db/` (evidence v
  `lkkl.migrace`, změněný provedený skript = chyba). Na serveru běží při startu kontejneru.
  Nový skript: zálohovat, napsat `NNN_nazev.sql`, spustit migraci (ne ručně přes psql).

## Obrazovky
13. **Samostatný design pro mobil a pro desktop** – ne jedna stránka, která se jen roztáhne.
    Každá obrazovka má návrh pro telefon (od šířky 375 px, ovládání palcem) i pro velkou
    obrazovku (víc informací najednou).
14. **Jednotný vizuální systém** definovaný dřív než první obrazovka: **tři velikosti písma**
    (12 / 15 / 20 px), bezpatkové; pevná sada mezer; barvy jen pro význam; štítky (badge);
    lety jako zaoblené pásky (připomínají stripy ŘLP); světlý i tmavý režim s přepínačem
    v aplikaci (podle zařízení / světlý / tmavý); hustě, ale čitelně. Makety:
    `docs/navrhy/lety-mobil-v4.html`, `pasek-mobil-v5.html`, `pruvodce-mobil-v4.html`, `osoby-mobil.html` (+ `osoby-mobil-v2.html` oprávnění), `muj-provoz-mobil.html`, `prihlaseni-mobil.html`; desktop `provoz-desktop-v7.html` (návrh `docs/modul-desktop.md`);
    tokeny v aplikaci `frontend/src/styly/tokeny.css`.
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
16. **Testovací a ostrý provoz bez automatiky** (revidováno 8. 10. 2026): hobby aplikace
    nahrazuje sešit, data jdou dál do účetního programu – nic se nezamyká ani hromadně
    nevyprazdňuje podle fáze. Funkce zkouší nejdřív uživatel (správce projektu), pak vybraní
    piloti (= aktivace jejich účtů), pak všichni – organizačně, ne v databázi. Vše běží v jedné
    databázi. **Žlutý pruh** „TESTOVACÍ PROVOZ“ řídí jen `lkkl.nastaveni.testovaci_provoz`
    (přepíná se přímo v databázi, oběma směry). Zkušební lety smaže admin po dnech:
    `CALL lkkl.smazat_lety_dne('RRRR-MM-DD');` (`DELETE` se zápisem do auditu). Celou tabulku
    letů ani audit nejde vyprázdnit příkazem `TRUNCATE` – obešel by audit.
    *K projednání:* jak testovat nové funkce po ostrém spuštění (např. příznak u účtu).
    Automatické testy u mě běží při každé změně.

## K projednání (převzato z první verze, zatím neplatí)
Projdeme jednotlivě, aby se nezanesl starý problém:
- oprávnění kontrolovat na serveru, ne jen ve frontendu;
- žádné e-maily členům před spuštěním; pozvánky jen ruční akcí admina;
- telefon osoby jen na vyžádání;
- hesla a klíče mimo git (proměnné prostředí);
- na server jedno SSH spojení (`ssh one12`, fail2ban banuje rychlá opakovaná spojení);
- soubory uživatele nepřepisovat ani nemazat (nové verze pod novým jménem);
- frontend (React?) a hosting (Docker ve VPS Centru).

## Nasazení
- **Nová verze nahrazuje první** na `https://lety.lkkl.cz` (stejná Docker aplikace ve VPS
  Centru, repozitář i databáze `lkkllog`); první verze je už jen kód ve větvi `v1`.
- Commit do main = jen kontroly a testy v CI. **Nasazení jen značkou `v2.<modul>.<oprava>`**
  (`git tag v2.1.0 && git push origin v2.1.0`) nebo ručním spuštěním workflow; značka
  se připíná až na pokyn uživatele. Návod a úklid po první verzi: `docs/nasazeni.md`.
- Kontrola stavu: `GET /api/health` (verze a spojení s databází).
