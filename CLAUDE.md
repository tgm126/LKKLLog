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
5. Dokud nejsou ostrá data, **migrace se nehromadí** – slučují se do jedné čisté.
6. **Data zadává uživatel** (číselníky, osoby, letadla…); žádné importy z Excelu.
7. **Tabulky:** stará verze je zinventarizovaná v `docs/tabulky-v1.md` (po spuštění nové
   verze se smažou).

## Datový model
6. **Normální formy:** každý údaj uložený jednou; odvozené hodnoty generovaným sloupcem
   nebo pohledem (view), ne kopií.
7. **Klíče a omezení:** umělý primární klíč + jedinečné přirozené klíče; cizí klíče všude bez
   kaskádového mazání; pravidla v databázi (CHECK, UNIQUE, EXCLUDE).
8. **Auditní log triggerem v databázi** (zachytí i přímou opravu v databázi).
9. Časy v UTC. Doménové názvy česky bez diakritiky, technické anglicky.
10. *K projednání:* zdroj pravdy o schématu – SQL (DDL, pohledy) vs. modely frameworku.

## Obrazovky
11. **Samostatný design pro mobil a pro desktop** – ne jedna stránka, která se jen roztáhne.
    Každá obrazovka má návrh pro telefon (od šířky 375 px, ovládání palcem) i pro velkou
    obrazovku (víc informací najednou).
12. **Jednotný vizuální systém** definovaný dřív než první obrazovka: dvě velikosti písma,
    pevná sada mezer, barvy jen pro význam, sdílené komponenty; hustě, ale čitelně.
13. Žádná vestavěná administrace frameworku; všechno, co admin dělá, je v aplikaci.
    Nouzové opravy přímo v databázi.

## Testování
14. Každá funkce prochází **třemi fázemi**:
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
- technologie (PostgreSQL, Python/Django, React) a hosting (Docker ve VPS Centru).

## Stav
- Server `https://lety.lkkl.cz` dál provozuje první verzi (větev `v1`). Případná oprava staré
  verze se dělá ve větvi `v1` a nasazuje značkou `v0.14.x` jako dosud.
- Hlavní větev zatím nemá nasazovací workflow – nic se z ní nenasazuje.
