# Modul: desktop – provozní deska

> **Odsouhlaseno 7. 10. 2026.** Změny nejdřív sem, pak do kódu.

Maketa: `docs/navrhy/provoz-desktop-v7.html` (klikací; obrazovka 1920 × 1080 a 1366 × 768,
světlý i tmavý režim). Starší `provoz-desktop.html`, `-v2` až `-v6` jsou překonané. Osoby, letadla a počasí v maketě jsou smyšlené.

## 1. Pro koho a kde

| Kde | Kdo | Co potřebuje | Obrazovka |
|---|---|---|---|
| Věž | služba na věži, časoměřič | vidět všechno, co letí, a rychle stisknout VZLET / PŘISTÁL; hodiny UTC, soumrak, počasí | monitor 1920 × 1080, myš, často celý den otevřené |
| Kancelář / doma | účetní | projít a opravit lety, plátce, doby, i za jiné dny; později deník za období a export | notebook 1366 × 768 (nebo 1920 při zvětšení 125–150 %) |
| Klubovna | piloti, instruktoři | podívat se na provoz; občas založit nebo naplánovat let | sdílený počítač, myš (přihlášení jen ke čtení odloženo, 6.1) |

Proto: **jedna obrazovka na celý provoz dne**, ovládaná myší, nic přes celou obrazovku,
**co nejvíc informací najednou** (místa je dost).

## 2. Zásady

- **Samostatné rozvržení**, ne roztažený mobil (pravidlo 13). Mobil zůstává, jak je.
- **Stejný vizuální systém:** tokeny z `tokeny.css` (barvy, písmo 12 / 15 / 20 px, mezery,
  pásky, štítky). Nové tokeny jen pro desktop: `--klik` 32 px a `--klik-hlavni` 40 px (myš
  místo palce; na mobilu dál 44 a 52 px), šířky sloupců a panelů, `--vyska-osy`,
  `--barva-najeti` (řádek pod myší), `--pismo-kod` (surová zpráva METAR/TAF – `VÝJIMKA`).
- **Kdy desktop:** okno široké **od 1200 px** (rozhoduje šířka, ne zařízení). 1366 px notebook
  i 1920 px při zvětšení 150 % (= 1280 px) tedy dostanou desktop. **Od 1500 px** přibude pravý
  sloupec Informace; užší okno ho má za tlačítkem v liště.
- **Myš:** co jde kliknout, reaguje na najetí (zvýraznění, u upravitelného pole ✎); popisky
  (`title`) doplní, co se nevejde (celý název úlohy, typ letadla, celá posádka).
- **Sluneční časy** (lišta, varování, časová osa) počítá server knihovnou `astral` pro moje
  letiště – i nautický a astronomický soumrak (Slunce 12° a 18° pod obzorem).
- **Klávesnice jen tam, kde zrychlí:** `N` nový let, `Esc` zavře panel, `Ctrl+Z` během 6 s
  vrátí poslední akci (jako tlačítko Zpět), v hledání osoby šipky a `Enter`, časy proběhlého
  letu se píšou z klávesnice (`13:05`). Zkratky pro VZLET / PŘISTÁL ne (omyl na špatném pásku).
- **Pásky se nepřetahují** myší (rozhodnuto 7. 10. 2026) – akce jsou jen tlačítka.

## 3. Rozvržení

```
┌ žlutý pruh fáze provozu ──────────────────────────────────────────────────────────────┐
│ AK Kladno Log  Provoz · Osoby · Letadla · (Deník)  ‹ Středa 7. 10. 2026 ›  TB SR SS TE do TE 2:40  14:21:05 UTC  TM │
│ [+ Nový let N]  KLUZÁKY [OK-0914 letí 4:16] [OK-2817 3× 25″] …  UL [OK-NUA 21 1× 37″ · na LKMB] │
├───────────────────────────────────┬────────────────────────────┬──────────────────────┤
│ VE VZDUCHU 5                      │ DENÍK DNE                  │ PLACHTAŘSKÝ PROVOZ   │
│ ▭ pásek  ▭ pásek  ▭ dvojice vleku │ jeden řádek na let         │ MOTOROVÝ PROVOZ      │
│ NAPLÁNOVANÉ 2                     │ (ukončené, pod nimi        │ POČASÍ (později)     │
│ ▭ pásek  ▭ pásek                  │ zrušené), patička celkem   │ DALŠÍ ZDROJE         │
├───────────────────────────────────┴────────────────────────────┴──────────────────────┤
│ ▾ ČASOVÁ OSA DNE  TB−1 h … TE+1 h   řádek = letadlo, úsečka = let, pásma soumraku, teď │
└───────────────────────────────────────────────────────────────────────────────────────┘
          detail letu / nový let = panel zprava přes deník a informace; pásky zůstanou vidět
```

- **Horní lišta:** název, navigace (Provoz, Osoby, Letadla; Deník šedě „později“), **den se
  šipkami** (3.6), sluneční časy se zbývajícím časem do konce soumraku (oranžově), hodiny UTC se
  sekundami, nabídka uživatele (Můj provoz, Režim zobrazení, Odhlásit – jako na mobilu).
  Jiné než domovské letiště = oranžový štítek s kódem jako na mobilu. Při přihlášení jen ke
  čtení (odloženo) oranžový štítek „Jen ke čtení“ a tlačítko „Přihlásit k úpravám“ (3.7).
- **Sloupce se posouvají každý zvlášť**, lišta, řada letadel a časová osa zůstávají.

### 3.1 Řada letadel
Pruh pod lištou se všemi letadly podle kategorie (na notebooku bez názvů kategorií, jen
přepážky). Rámečky jsou **neutrální**; stav ukazuje jen **proužek vlevo** (zelený letí, modrý
naplánované) – barevnou plochou je jen pásek. Každé letadlo má dva řádky: rejstřík a **stav
dneška**:
- letí → běžící čas („letí 0:08“), naplánované → „naplánován“;
- jinak počet letů a nálet dne („3× 25″“) nebo „dnes nelétal“;
- **kde je**: přistálo-li naposledy jinde než na mém letišti, oranžově „na LKMB“ (odvozeno
  z místa posledního přistání, nic se neukládá);
- mimo provoz přeškrtnuté, nejde vybrat.

Klik na letadlo **na zemi** otevře formulář nového letu s tímto letadlem už vybraným (ušetří
výběr letadla); klik na letící nebo naplánované ukáže jeho pásek a detail. Tlačítko „+ Nový
let“ (`N`) otevře formulář bez letadla. Větší flotila se posouvá do strany.

### 3.2 Pásek (desktop)
Vodorovná řada přihrádek se svislými přepážkami – jako papírový strip ŘLP:

| Letadlo | Posádka | Štítky | Trasa | Čas | Akce |
|---|---|---|---|---|---|
| rejstřík 20 px, typ (u vleku „vlečná“) | osoba na řádek s funkcí | 2 × 2 v pevných pozicích: účel · způsob vzletu / POB · úloha (po najetí celý název) | jen když let není z mého letiště na moje: odkud nahoře, → kam dole; moje letiště šedě, jiné tučně (jinak prázdná) | stopky + ↑ čas vzletu; u naplánovaného „plán“ a kdy byl založen (po najetí kdo) | T&G n · PŘISTÁL / VZLET |

- Barvy, okraje, varovný řádek, dvojitý pásek vleku a pravidla zobrazení (běžné hodnoty se
  nevypisují, prázdná pozice zůstane prázdná) **beze změny proti mobilu** (`modul-lety.md` 3.1).
  Trasa jako na mobilu – jen když nejde o moje letiště (rozhodnuto 7. 10. 2026; „LKKL → LKKL“
  na každém pásku byl jen šum).
- **Na pásku žádné barevné písmo** (rozhodnuto 7. 10. 2026): stav letu říká jen **výplň pásku**
  (zelená ve vzduchu, modrá naplánovaný, červená problém). Stopky jsou v barvě textu (i na
  mobilu); jedinou výjimkou je **text varování – červeně** jako na mobilu.
- **Tlačítka sjednocená s mobilem** (rozhodnuto 7. 10. 2026): **PŘISTÁL** zeleně a **VZLET** modře
  plné s bílým textem (na pásku pevná šířka 112 px), **T&G** bílé s černým textem – na pásku
  i v detailu, na desktopu i na mobilu.
- Přihrádky mají pevnou šířku, takže stejný údaj je u všech pásků pod sebou; posádka bere zbytek.
  Štítky jsou **vždy stejný typ na stejném místě** vodorovně i svisle: prázdná pozice má šířku
  i výšku štítku (oba řádky štítků stejně vysoké), takže chybějící účel a způsob vzletu POB
  neposune nahoru.
- Klik kamkoli mimo tlačítka = detail letu. **Vybraný pásek** (otevřený detail) má výrazný
  prstenec v barvě textu s mezerou – vidět v obou režimech; stejně vybraný let na časové ose. Samostatné tlačítko
  pro detail („⋯“) není – bylo by nadbytečné (rozhodnuto 7. 10. 2026).
- Pořadí: ve vzduchu podle času vzletu (nejdéle letící nahoře), naplánované podle založení.

### 3.3 Deník dne
- **Jeden řádek na let** (rozhodnuto 7. 10. 2026): Letadlo · Posádka (PIC · druhá osoba
  s funkcí) · ↑ · ↓ · Doba · P. Ostatní údaje (účel, způsob vzletu, úloha, POB, trasa, plátce,
  poznámka, u zrušeného důvod) jsou v **detailu** po kliknutí na řádek. Na monitoru věže je
  vidět celý den bez posouvání.
- Stejně i u **jiného dne** (3.6) – deník je jen širší (zabere i místo pásků).
- Ukončené od posledního přistání, pod nimi oddíl Zrušené (přeškrtnutý rejstřík).
  Patička: lety, doba, přistání. Celá posádka s funkcemi v popisku řádku.

### 3.4 Informace (pravý sloupec)
Svislý sloupec **karet**; každá karta je samostatný zdroj, přidávají se postupně:
1. **Plachtařský provoz:** nahoře **P** (počet přistání kluzáků), **doba letů** kluzáků
   a **doba vleků**; pod tím tabulka kluzáků a vlečných (Letadlo · Doba · P).
2. **Motorový provoz:** nahoře **P** a **doba letů**; pod tím tabulka letadel (Letadlo ·
   Doba · P).

   Počet letů se v souhrnech neuvádí, jen počet přistání (P jako v deníku). Hlavička karty
   má jen název; rozpad podle startů a účelu ani sloupec „kde je“ není (rozhodnuto
   7. 10. 2026; kde letadlo je, ukazuje řada letadel).

   Zařazení podle letu: let kluzáku nebo vlečný let (let s vazbou na kluzák) = plachtařský;
   ostatní = motorový, včetně **TMG** (rozhodnuto 7. 10. 2026) a vlastních letů vlečné mimo vlek.
   Součet obou dohromady se neukazuje.
3. **Počasí – METAR/TAF** (později, samostatný modul): v maketě jen ukázka místa. Kladno
   METAR nevydává, nabízí se nejbližší stanice (LKPR Ruzyně, případně další), surová zpráva
   + rozepsané hlavní údaje (vítr, dohlednost, oblačnost, teplota, QNH), stáří zprávy.
4. **Další zdroje** (prázdné místo): NOTAM, AUP/UUP (aktivace prostorů), GAMET, radar srážek,
   stav letadel z údržby…

Karty 1 a 2 se počítají z letů dne (pohledem nebo dotazem nad `v_let`), nic se neukládá.
Karta „Piloti dnes“ z v2 vypuštěna (7. 10. 2026 – nemá praktický užitek). Kde letadlo je,
ukazuje řada letadel (3.1).

### 3.5 Časová osa dne
Pás dole přes celou šířku: **řádek = letadlo, které ten den letělo**, úsečka = let od vzletu do
přistání (ukončený plnou šedou, vlek světlejší šedou, nejméně 6 px – i krátký let kluzáku se
čte jako úsečka; letící roste do „teď“ sytě zeleně, přes varování sytě červeně – v obou
režimech stejné akční barvy), stupnice po
hodinách, modrá čára „teď“. Na první pohled je vidět, kdy co létalo, mezery a dlouhé lety;
účetní pozná zapomenuté přistání. Klik na úsečku = detail, popisek = rejstřík, časy, posádka.
Kliknutím na nadpis se sbalí; na notebooku je sbalená od začátku.

- **Rozsah podle dne** (rozhodnuto 7. 10. 2026): od hodiny před začátkem občanského soumraku
  (TB) do hodiny po jeho konci (TE); vždy obsáhne i všechny lety dne. Pro LKKL: 7. 10.
  03:35–18:06, 21. 12. 05:16–16:47, 21. 6. 01:01–21:08 UTC.
- **Pásma soumraku barevnou výplní** ráno i večer: občanský (TB–SR, SS–TE), nautický,
  astronomický a noc – čím dál od dne, tím tmavší, ale jen jemně (pozadí, ne hlavní informace) (tokeny `--barva-soumrak-obcansky`,
  `--barva-soumrak-nauticky`, `--barva-soumrak-astronomicky`, `--barva-noc`, každý se světlou
  i tmavou hodnotou). Den je bez výplně. Najetí myší na pásmo ukáže jeho časy. V létě na naší
  zeměpisné šířce astronomická noc nenastane (zhruba od konce května do poloviny července) –
  pásmo astronomického soumraku pak sahá až k okraji osy.
- `GET /api/den` vrátí navíc začátek a konec nautického a astronomického soumraku (prázdné,
  když nenastane).

### 3.6 Jiný den
Šipky ‹ › v liště listují dny (dopředu nejvýš do dneška). Pod lištou modrý pruh „Prohlížíte
úterý 6. 10. 2026 · Zpět na dnešek“. Jiný den nemá pásky (ty patří jen k dnešku), deník je
širší (3.3), souhrny a časová osa jsou za vybraný den, řada letadel ukazuje dál
současný stav. Úpravy letů jiného dne stejně jako dnes (omezí je až uzávěrky). Rozhraní
`GET /api/lety?den=` a `GET /api/den?den=` už existuje.

### 3.7 Přihlášení jen ke čtení (pro klubovnu)
**Odloženo** (6.1). Až se bude dělat, na desktopu v režimu jen ke čtení: chybí „+ Nový let“, akce na páscích a v detailu,
pole v detailu nejdou upravit, klik na letadlo na zemi nic nezaloží; v liště oranžový štítek
„Jen ke čtení“ a „Přihlásit k úpravám“. Totéž na mobilu.

### 3.8 Detail letu a nový let – panel zprava
- Panely sahají od řady letadel **až dolů přes časovou osu** (víc místa, méně posouvání).
- **Detail** (620 px) vyjede zprava přes deník; pásky zůstanou vidět **a dál se ovládají** –
  věž může stisknout PŘISTÁL u jiného letu, aniž by detail zavírala. Obsah a pravidla úprav
  stejné jako na mobilu (`modul-lety.md` 3.5): pásek nahoře, bloky Posádka a let · Časy
  a místa · Platba a poznámka · Evidence s historií (u zrušeného i důvod zrušení). **Bez horní
  lišty s rejstříkem** (rozhodnuto 7. 10. 2026 – rejstřík je hned v pásku): pásek je úplně
  nahoře a vedle něj vpravo zavírací křížek (a `Esc`); pásek se vejde na jeden řádek i s trasou. Úprava **přímo v poli** (klik → pole
  k zápisu nebo nabídka, `Enter` uloží, `Esc` vrátí). Akce v patičce.
- **Nový let** (820 px) je **jeden formulář místo průvodce** (rozhodnuto 7. 10. 2026): nahoře
  rozpracovaný pásek (čárkovaný, u aerovleku dvojice), vlevo Letadlo (dlaždice podle kategorií
  a stavu) · Účel a vzlet (segmenty) · Vlek; vpravo Posádka · Úloha (osnova → seznam) · Další
  údaje (místa, plátce, poznámka). Chybějící povinná volba má v hlavičce bloku „vyberte“
  a patička vypíše „Chybí: …“. Patička: VZLET TEĎ · NAPLÁNOVAT · PROBĚHLÝ LET… (ukáže pole časů).
  Pravidla a nabídky stejné jako průvodce; na mobilu průvodce zůstává.
- **Osoby:** rychlá volba čipy podle oprávnění a mého provozu (stejná pravidla jako průvodce)
  + **pole „Hledat…“ s našeptáváním** (bez diakritiky, podle jména i příjmení) místo
  samostatné obrazovky hledání.
- Adresy zůstávají (`/let/:id`, `/novy-let`): na desktopu otevřou panel nad deskou, na mobilu
  celou obrazovku – odkaz funguje na obou.

## 4. Technické řešení (frontend)

- **Stejné rozhraní (API) a data** – desktop nepotřebuje nové tabulky; souhrny provozu, „kde
  je“ a časová osa se počítají z letů dne (případně jeden nový pohled pro souhrn, rozhodne se
  při psaní kódu). Jiný den používá existující `?den=`.
- Volba rozvržení podle šířky okna (`matchMedia("(min-width: 1200px)")`, přepne se i při
  změně velikosti okna). Sdílené: načítání dat (`lety/api.ts`, obnovování 10 s), akce letu
  a Zpět, pravidla nabídek osob, štítek, tlačítko, výběr místa. Vlastní desktopové:
  stránka `stranky/Deska.tsx`, `lety/PasekRadek.tsx` (pásek v řadě přihrádek),
  `lety/RadaLetadel.tsx`, `lety/DenikTabulka.tsx`, `lety/CasovaOsa.tsx`, `lety/NovyLet.tsx`
  (formulář v jednom), `komponenty/Panel.tsx`, `komponenty/Naseptavac.tsx`,
  `komponenty/Karta.tsx`.
- Styly dál jen z tokenů; desktopové komponenty mají vlastní CSS. Polohy úseček časové osy
  přes vlastní proměnné komponenty (`--od`, `--do`), ne vložené styly. Kontrola stylů beze změny.
- **Testy:** klikací testy (Playwright) navíc v rozměru 1366 × 768 a 1920 × 1080: deska
  (pásky, deník, řada letadel, časová osa), nový let z řady letadel i klávesou N, VZLET →
  PŘISTÁL → Zpět (i Ctrl+Z), detail s úpravou na místě, panel otevřený a zároveň akce na
  jiném pásku, jiný den (širší deník, bez pásků).

## 5. Postup (malé moduly) – odsouhlaseno 7. 10. 2026

1. **Provozní deska** – vše v kap. 3 kromě 3.7 a počasí. (Tento návrh.)
2. **Osoby a Letadla na desktopu** – seznam vlevo, detail vpravo (vlastní krátký návrh).
3. **Můj provoz na desktopu** – v nabídce uživatele (malá úprava).
4. **Počasí** – zdroj, stanice, mezipaměť na serveru (vlastní návrh).
5. Později: přihlášení jen ke čtení (6.1), deník za období (účetní), uzávěrky, export, velký
   displej.

## 6. Rozhodnutí a otázky

**Rozhodnuto 7. 10. 2026:** pásky se nepřetahují; jiný den ano (3.6); nový let jako jeden
formulář; postup podle kap. 5; zobrazovat maximum informací (řada letadel, časová osa); souhrn zvlášť pro plachtařský a motorový provoz (P = počet přistání, doba letů,
u plachtařů doba vleků, tabulka letadel Doba · P; bez počtu letů, rozpadu, sloupce „kde je“
a textu v hlavičce), TMG do motorového provozu, bez karty Piloti dnes; deník jeden řádek na let, zbytek
v detailu; pásek bez „⋯“; klidnější deska (na pásku žádné barevné písmo kromě tlačítek PŘISTÁL a VZLET, T&G bílé
s černým textem i na mobilu, detail bez lišty s rejstříkem, neutrální řada
letadel s proužkem stavu, trasa jen mimo moje letiště, výrazný vybraný pásek, jemnější osa,
panely až dolů); časová osa podle dne s pásmy soumraku; přihlášení jen ke čtení
odloženo.

### 6.1 Přihlášení jen ke čtení – ODLOŽENO (7. 10. 2026: zatím se nedělá)
Návrh zůstává pro pozdější rozhodnutí včetně otázek níže.

Problém: na sdíleném počítači (klubovna) platí přihlášení 30 dní a kolemjdoucí by jednal pod
cizím jménem – audit by zapsal nesprávnou osobu.

- U přihlášení zaškrtávátko **„Jen ke čtení (sdílený počítač)“**. Je to vlastnost **relace**
  (zařízení), ne účtu:
  ```sql
  ALTER TABLE lkkl.relace ADD COLUMN jen_cteni boolean NOT NULL DEFAULT false;
  ```
  Bez auditu (relace audit nemají); přihlášení se zapisuje jako dosud.
- **Hlídá server:** každý zápis (`POST` mimo přihlášení a odhlášení) v relaci jen ke čtení
  vrátí 403 „Přihlášeno jen ke čtení“ – jedna společná kontrola pro všechny endpointy, test,
  že ji žádný zápis neobejde. Skrytí tlačítek ve frontendu je jen pohodlí.
- Relace jen ke čtení platí 30 dní jako ostatní (počítač v klubovně zůstane přihlášený).
- `GET /api/ja` vrátí `jen_cteni`; podle něj frontend skryje ovládání (3.7).
- „Můj provoz“ (letiště, osoby v provozu) zůstává i v relaci jen ke čtení povolený? Je to
  nastavení zařízení, ne údaj letu. *Doporučuji ano* (je to jediný zápis, který se povolí).

*Otázka:* co udělá **„Přihlásit k úpravám“**?
- **a) Jednoduše** (doporučuji na začátek): běžné přihlášení vlastním e-mailem a heslem
  nahradí relaci jen ke čtení; po práci se člověk odhlásí a kdokoli přihlásí počítač znovu
  jen ke čtení. Riziko: zapomene se odhlásit.
- **b) Dočasně:** úpravové přihlášení platí jen 15 minut od poslední aktivity a pak se
  zařízení samo vrátí do relace jen ke čtení (dvě relace na zařízení). Bezpečnější, ale
  složitější; jde doplnit později bez změny a).

### 6.2 Další otázky
1. **Písmo 12 / 15 / 20 px i na desktopu.** Na věži z dálky stačí zvětšení prohlížeče
   (`Ctrl +`); rozvržení s ním počítá (1920 při 125 % = 1536 px, Informace zůstanou).
   Čtvrtou velikost (např. hodiny) zatím nezavádím.
2. **Počasí – zdroj.** Kandidát: veřejné API `aviationweather.gov` (METAR/TAF ve formátu JSON,
   bez klíče), stahuje server a drží 5–10 minut v paměti (žádná tabulka, nejde o naše data);
   stanice jako číselník nebo příznak u letiště. Rozhodne se v modulu Počasí.
