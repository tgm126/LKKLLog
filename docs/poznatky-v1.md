# Poznatky z první verze (v1, do v0.14.3)

Sepsáno 5. 10. 2026 před novým začátkem. První verze běžela v testovacím provozu na
`https://lety.lkkl.cz`. Po konzultaci s uživateli se aplikace staví znovu od datového modelu.
Důvodem není nefunkčnost, ale kód zatížený opravami oprav, převody dat a návraty ze slepých
uliček.

**Kde najít starou verzi:** větev `v1` a značka `v1-final` v tomto repozitáři. Ke čtení je
rozbalená ve složce `C:\GIT\LKKLLog-v1` (git worktree). Původní návrh je v
`docs/podklady/navrh-v1.md`. Je to hlavní zdroj doménových pravidel, ale datový model
v něm je ten starý.

Tento dokument zachycuje, co není v ostatních podkladech: rozhodnutí z rozhovorů,
připomínky uživatelů, slepé uličky a technické pasti.

---

## 1. Co se osvědčilo (převzít jako zásady)

- **Čas „teď“ určuje server**, ne telefon. Vše v UTC, let patří ke dni podle data vzletu
  v UTC. Doba letu = (přistání − vzlet) zaokrouhlená na celé minuty (30 s a víc nahoru),
  počítaná v databázi (generovaný sloupec). Python `round()` je bankovní, nepoužívat.
- **Idempotence stisků** VZLET/PŘISTÁL: platí první, druhý dostane „Už ukončeno ve … (kdo)“.
- **Optimistické zamykání** oprav (číslo verze záznamu).
- **Pojistky v databázi:** jeden let letadla v čase (EXCLUDE), jedno domovské letiště,
  auditní log jen pro zápis (trigger).
- **Nic se nemaže:** let se ruší s důvodem, číselníky se deaktivují.
- **Průvodce novým letem jen ťukáním:** letadlo → účel → posádka → … , předvyplnění, nejčastější
  volby nahoře.
- **Nabídky posádky jen s vhodnými lidmi** (PIC s průkazem pro kategorii a přeškolením na typ,
  instruktor, vlekař…) a tlačítko *Ukázat i ostatní*. Když nikdo vhodný není, nabídnou se všichni.
- **Hlídání dokladů a rozlétanosti jen varuje, nikdy neblokuje.** Moduly se zapínají
  přepínači (způsobilost pilotů, rozlétanost, způsobilost letadel), až jsou data kompletní.
- **Velký displej** na tajný odkaz bez přihlášení (zneplatnitelný): probíhající lety, UTC se
  sekundami, západ slunce a konec občanského soumraku (knihovna `astral`), zvýraznění letů
  přes maximální dobu nebo po soumraku.
- **Upozornění na neukončené lety** e-mailem i **Web Push** notifikací (na iPhonu jen po
  přidání aplikace na plochu). Klíč VAPID odvozený z tajného klíče aplikace.
- **Automatická denní uzávěrka** druhý den v 5:00 českého času (cron na serveru), pokud ji
  večer neudělal časoměřič nebo věž. Uzávěrky mají verze a přehled „změny po uzávěrce“.
- **Testovací provoz:** žlutý pruh „TESTOVACÍ PROVOZ – data nejsou skutečná“, příznak
  *testovací* u osob a poznámka „testovací“ u testovacích dat, aby šla před spuštěním uklidit.
- **Nasazení jen značkou verze**, klikací testy (Playwright) v CI a nasazení čeká, až projdou.
- **Kompaktní vzhled:** hustě, ale čitelně – dvě velikosti písma (14 px obsah, 12 px šedé
  popisky), barvy jen pro význam (zelená v pořádku, oranžová brzy vyprší, červená neplatné),
  málo odsazení, tabulky místo karet. Řídký „roztahaný“ design uživatel výslovně odmítl.

## 2. Slepé uličky a co dělat jinak

- **Hromadný import číselníků z Excelu** (šablona, načtení) – zrušen. Data se zadávají přes
  karty s předvyplněnými číselníky.
- **Licence a medical si zadával pilot sám** na vlastní obrazovce – zrušeno, zadává admin
  (případně správce) na kartě osoby.
- **Tabulka „oprávnění“ s úrovněmi žák / pilot / instruktor / examinátor** – nahrazena
  doklady: průkaz osoby + kvalifikace z číselníku, výcvik (žák), přeškolení na typ, provozní
  oprávnění. Úroveň se z dokladů odvozuje, neukládá.
- **Redundantní sloupce:** letadlo mělo textový typ a kategorii a k tomu odkaz na typ
  z číselníku (kopie se synchronizovaly v `save()`); termíny letadel měly textový název
  a později odkaz na druh. V novém modelu jen odkaz, odvozené hodnoty přes pohled.
- **Dvojí administrace:** vestavěná Django administrace vedle vlastních obrazovek mátla
  (uživatel hledal změny jinde). V nové verzi žádná Django administrace, vše v aplikaci;
  nouzové opravy přímo v databázi.
- **Hromadění migrací s převody dat** (etapa 14: 0010–0014 jen kvůli přestavbě modelu).
  Dokud nejsou ostrá data, migrace slučovat.
- **Číselníky přidávané postupně** po etapách skončily roztroušené (část v aplikaci lety,
  část v aplikaci číselníky). Navrhnout je najednou na začátku.

## 3. Doménová rozhodnutí z rozhovorů s uživatelem

### Osoby a doklady
- Hierarchie: žák → pilot → instruktor → examinátor; k tomu vlekař, navijákář.
- **Přeškolení je na typ letadla** (platí pro všechna letadla typu, např. všechny Blaníky).
- **Provozní oprávnění** (klubová): navijákář, služba RADIO, vyhlídkové lety.
- **Medical:** jen třída a platnost; jeden medical může pokrývat dvě třídy (platnost se eviduje
  pro každou třídu zvlášť). Který medical je potřeba, se posuzuje podle licence (PPL → třída 2,
  LAPL → LAPL medical nebo vyšší…).
- **Radiofonní průkaz ČTÚ:** omezený (OFL) a všeobecný (VFL) – „ČTÚ průkaz“ = radiofonní průkaz.
- **Jazyková způsobilost:** čeština nemá smysl (licence na češtinu neexistuje); angličtina
  ICAO 4/5/6 jen jako informace, nehlídá se.
- **Žák:** před prvním sólem musí mít medical a radiofonní průkaz; ve výcviku (zahájen,
  sólo povoleno, ukončen) se mu nehlídá rozlétanost, jen informace.
- **Rozlétanost:** 3 starty a přistání za 90 dní pro cestující, 12/24 měsíců podle licence
  (FCL.060, FCL.140.A, FCL.740.A, SFCL.160, ULL), let s instruktorem; vlekař aspoň 5 vleků
  za 24 měsíců (FCL.805, SFCL.205) – varuje se jen při zakládání vleku. Podrobně
  `podklady/licence-a-rozletanost.md`.
- **Externí osoby** nemají e-mail ani přihlášení.
- **Telefon** se nikdy neukazuje v seznamech, číselnících ani na displeji, jen na vyžádání
  (samostatné volání po ťuknutí na „Zobrazit telefon“), pro všechny přihlášené.
- Role v aplikaci: časoměřič / věž, účetní, správce licencí a letadel, admin. Role mění jen admin.
  Roli technika uživatel nechce.

### Letadla
- Kategorie: motorové, TMG, kluzák, UL. Typ z číselníku určuje kategorii.
- **Stav provozního deníku při spuštění** (celkový nálet a starty k datu) + lety z evidence
  = aktuální nálet. Bez toho nesedí termíny podle náletu.
- **Termíny** jen jednoduše: do data nebo do celkového náletu (při obou platí, co nastane dřív),
  varování 30 dní, resp. 10 h předem. Žádné plánování údržby, žádné životnosti dílů.
- Maximální doba letu (s plnými nádržemi, u kluzáků prázdné), vlečné, soukromé (neexportuje
  se pro účetnictví), pořadí v nabídkách.

### Lety a provoz
- Běžící čas letu se sekundami.
- **T&G a „Přistál“ během letu jen u motorových** (ne kluzák). **Počet přistání vždy zapsat**;
  časy jednotlivých T&G jsou „nice to have“.
- Násobky přistání musí být na displeji srozumitelné (uživatel nevěděl, co znamená číslo
  za časem; součet nesouhlasil s „přistání 15“).
- **Dodatečný zápis** proběhlého letu (pilot létající sám) s označením *zapsaný dodatečně*;
  pilot do denní uzávěrky, potom časoměřič nebo účetní.
- Kdo uzavírá den: časoměřič nebo věž; jinak automaticky ráno.
- Plátce letu, velmi krátké lety (přetržené lano) – viz `podklady/navrh-v1.md` kap. 3.
- **OGN** (Open Glider Network): později kontrola souladu s logbookem.

### Komunikace s členy
- **Žádné předčasné e-maily.** Režim odesílání: vypnuto / jen povolené adresy / všem.
  Pozvánky jen ruční akcí admina (vybraným nebo všem), nikdy automaticky při založení osoby.
- **SMS upozornění:** nerozhodnuto (jaká brána, komu).

### Plány
- Import starších letů z Flight Office (nálet a rozlétanost z nich).
- Manuál a nápověda (podklady o předpisech jsou připravené).
- Úklid testovacích dat před ostrým spuštěním.
- Ceny a sazby – samostatná analýza, mimo první verzi.

## 4. Technické pasti

- **VPS Centrum:** nginx blokuje cesty a subdomény `config|tmp|temp|log|logs|bin|inc` (403).
  Kontejner běží pod uživatelem domény, kód je připojený na `/app` (aplikace proto v image
  jinde), limit paměti 512 MB, server má málo volné RAM. Podrobně `podklady/provoz.md`.
- **SSH:** `ssh one12`; fail2ban banuje rychlá opakovaná spojení – vše v jedné relaci.
- **Cron** na serveru v `/etc/cron.d/lkkllog` (skript údržby), instalovat v jedné SSH relaci.
- **Databáze na serveru** přes unixový socket a proměnné `DB_*`, migrace při startu kontejneru.
- **Windows:** v `DATABASE_URL` `127.0.0.1`, ne `localhost`. Dlouhé bash heredoc skripty
  padají na uvozovkách – psát skripty do souboru.
- **CI:** kontrolovat i chybějící migrace (`makemigrations --check`).
- **Klikací testy (Playwright):**
  - transakční testy vyprázdní databázi včetně výchozích číselníků → znovu naplnit ve fixture;
  - po přechodu stránky vždy nejdřív ověřit nadpis nové stránky (jinak souběh);
  - fixture přihlášení sdílela jednoho klienta → kontroly jiného uživatele až na konci testu;
  - text „ve vzduchu“ se po soumraku objevil dvakrát → hledat podle role (nadpis), ne textu.
- **Mantine 9:** `Grid` má `gap` (ne `gutter`), `Group` nemá `rowGap` (jen přes `style`).
- **TanStack Query:** pozor na kolize klíčů dotazů (`['ciselniky']` použitý pro dvě různá data).
- **Uspaný telefon:** po odemčení hned znovu načíst data.
- **E-mail:** bez SPF a DKIM padá pošta do spamu (nastaveno, viz provoz).
