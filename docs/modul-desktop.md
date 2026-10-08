# Modul: desktop – provozní deska

> **Odsouhlaseno 7. 10. 2026.** Změny nejdřív sem, pak do kódu.

Maketa: `docs/navrhy/provoz-desktop-v7.html` (klikací; obrazovka 1920 × 1080 a 1366 × 768,
světlý i tmavý režim). Starší `provoz-desktop.html`, `-v2` až `-v6` jsou překonané. Osoby, letadla a počasí v maketě jsou smyšlené.

## 1. Pro koho a kde

| Kde | Kdo | Co potřebuje | Obrazovka |
|---|---|---|---|
| Věž | služba na věži, časoměřič | vidět všechno, co letí, a rychle stisknout VZLET / PŘISTÁL; hodiny UTC, soumrak, počasí | monitor 1920 × 1080, myš, často celý den otevřené |
| Kancelář / doma | účetní | projít a opravit lety, plátce, doby, i za jiné dny; později deník za období a export | notebook 1366 × 768 (nebo 1920 při zvětšení 125–150 %) |
| Klubovna | piloti, instruktoři | podívat se na provoz; občas založit nebo naplánovat let | sdílený počítač, myš, **přihlášení jen ke čtení** (6.1) |

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
  sloupec souhrnů; užší okno ho má za tlačítkem „Souhrny“ v liště. Hranice jsou v kódu
  (`rozvrzeni.ts`), ne v CSS – rozvržení vybírá jiné komponenty a pevné rozměry patří jen do
  tokenů.
- **Ovládání myší:** uvnitř desky mají tokeny `--dotyk` a `--dotyk-hlavni` hodnoty pro myš
  (32 a 40 px), takže sdílené volby, čipy a pole z mobilu se zmenší samy.
- **Myš:** co jde kliknout, reaguje na najetí (zvýraznění, u upravitelného pole ✎); popisky
  (`title`) doplní, co se nevejde (celý název úlohy, typ letadla, celá posádka).
- **Sluneční časy** (lišta, varování, časová osa) počítá server knihovnou `astral` pro moje
  letiště – i nautický a astronomický soumrak (Slunce 12° a 18° pod obzorem).
- **Klávesnice jen tam, kde zrychlí:** `N` nový let, `Esc` zavře panel, `Ctrl+Z` během 6 s
  vrátí poslední akci (jako tlačítko Zpět); v poli pro text klávesy nepůsobí. Zkratky pro
  VZLET / PŘISTÁL ne (omyl na špatném pásku). Časy proběhlého letu a úpravy časů zatím
  výběrem z mřížky jako na mobilu (psaní z klávesnice případně později).
- **Pásky se nepřetahují** myší (rozhodnuto 7. 10. 2026) – akce jsou jen tlačítka.

## 3. Rozvržení

```
┌ žlutý pruh testovacího provozu ───────────────────────────────────────────────────────┐
│ AK Kladno Log                       ‹ Středa 7. 10. 2026 ›  TB SR SS TE do TE 2:40  14:21:05 UTC  TM │
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

- **Desktop je jedna stránka** (rozhodnuto 8. 10. 2026): jen provozní deska, **bez menu**.
  Správa osob a letadel je jen na mobilu (na desktopu adresa `/osoby`, `/letadla` vede na
  desku); můj provoz zatím jako sloupec uprostřed z nabídky uživatele.
- **Horní lišta:** název, datum normálním písmem 15 px, **den se
  šipkami** (3.6), všechny údaje na jednom účaří písma, sluneční časy se zbývajícím časem do konce soumraku (oranžově), hodiny UTC se
  sekundami, nabídka uživatele (Můj provoz, Režim zobrazení, Odhlásit – jako na mobilu).
  Jiné než domovské letiště = oranžový štítek s kódem jako na mobilu. Při přihlášení jen ke
  čtení oranžový štítek „Jen ke čtení“ (3.7).
- **Sloupce se posouvají každý zvlášť**, lišta, řada letadel a časová osa zůstávají.

### 3.1 Řada letadel
Pruh pod lištou se všemi letadly podle kategorie (na notebooku bez názvů kategorií, jen
přepážky). Rámečky jsou **neutrální**; stav ukazuje jen **proužek vlevo** (zelený letí, modrý
naplánované) – barevnou plochou je jen pásek. Každé letadlo má dva řádky: rejstřík a **stav
dneška**:
- letí → běžící čas („letí 0:08“), naplánované → „naplánován“;
- jinak jen nálet dne („25″“, bez počtu letů – rozhodnuto 8. 10. 2026) nebo „dnes nelétal“;
- **kde je**: přistálo-li naposledy jinde než na mém letišti, oranžově kód letiště („LKMB“,
  bez „na“ – 8. 10. 2026; odvozeno z místa posledního přistání, nic se neukládá);
- mimo provoz přeškrtnuté, nejde vybrat.

Klik na letadlo **na zemi** otevře formulář nového letu s tímto letadlem už vybraným (ušetří
výběr letadla); klik na letící nebo naplánované ukáže jeho pásek a detail. Tlačítko „Nový
let“ (bez „+“ a bez značky klávesy, klávesa `N` funguje dál) otevře formulář bez letadla.
Větší flotila se posouvá do strany.

### 3.2 Pásek (desktop)
Vodorovná řada přihrádek – jako papírový strip ŘLP – a pod ní řádek štítků (upraveno
8. 10. 2026: štítky z vlastní přihrádky do třetího řádku, přihrádka trasy zrušena, posádka
má víc místa; **bez svislých přepážek**, trasa pod časem, sloupec pásků nejvýš 760 px):

| Letadlo | Posádka | Čas | Akce |
|---|---|---|---|
| rejstřík 20 px, typ (u vleku „vlečná“) | osoba na řádek s funkcí (bere všechno zbylé místo) | stopky + ↗ čas vzletu; u naplánovaného „plán“ a kdy byl založen (po najetí kdo) | T&G n · PŘISTÁL / VZLET |

- **Třetí řádek přes celou šířku:** štítky v pevných pozicích zleva účel · způsob vzletu ·
  POB · úloha (po najetí celý název) – stejná komponenta jako na mobilu; **pod časem vždy
  trasa** odkud → kam jako štítek (moje letiště šedě, jiné tučně; výrazná kreslená šipka jako
  u časů). Akce jsou vpravo svisle uprostřed přes oba řádky.
- Přihrádky odshora, první řádky na jednom účaří: rejstřík, první z posádky a stopky (jeden
  pilot je v řádku s rejstříkem, ne uprostřed výšky).
- Akce nemají přepážku – tlačítka mají vlastní okraj; T&G se nelepí na čáru (8. 10. 2026).
  Sloupec akcí má pevnou šířku, aby PŘISTÁL / VZLET byly u všech pásků pod sebou.
- Barvy, okraje, varovný řádek, dvojitý pásek vleku a pravidla zobrazení (běžné hodnoty se
  nevypisují, prázdná pozice zůstane prázdná) **beze změny proti mobilu** (`modul-lety.md` 3.1).
  Trasa na desktopu **vždy** (rozhodnuto 8. 10. 2026 – ve třetím řádku je místo; nahrazuje
  rozhodnutí 7. 10. ukazovat ji jen mimo moje letiště). Na mobilu dál jen jedna strana mimo
  moje letiště (`modul-lety.md`).
- **Na pásku žádné barevné písmo** (rozhodnuto 7. 10. 2026): stav letu říká jen **výplň pásku**
  (zelená ve vzduchu, modrá naplánovaný, červená problém). Stopky jsou v barvě textu (i na
  mobilu); jedinou výjimkou je **text varování – červeně** jako na mobilu.
- **Tlačítka sjednocená s mobilem** (rozhodnuto 7. 10. 2026): **PŘISTÁL** zeleně a **VZLET** modře
  plné s bílým textem (na pásku pevná šířka 112 px), **T&G** bílé s černým textem – na pásku
  i v detailu, na desktopu i na mobilu.
- Přihrádky mají pevnou šířku, takže stejný údaj je u všech pásků pod sebou; posádka bere zbytek.
  Štítky jsou **vždy stejný typ na stejném místě**: prázdná pozice má šířku štítku, takže
  chybějící účel a způsob vzletu POB neposune doleva.
- Klik kamkoli mimo tlačítka = detail letu. Pod myší se pásek nezvýrazňuje (rozhodnuto
  8. 10. 2026). **Vybraný pásek** (otevřený detail) má výrazný prstenec v barvě textu
  s mezerou – vidět v obou režimech; stejně vybraný let na časové ose. Samostatné tlačítko
  pro detail („⋯“) není – bylo by nadbytečné (rozhodnuto 7. 10. 2026).
- Pořadí: ve vzduchu podle času vzletu (nejdéle letící nahoře), naplánované podle založení.

### 3.3 Deník dne
- **Jeden řádek na let** (rozhodnuto 7. 10. 2026): Letadlo · Posádka (PIC · druhá osoba
  s funkcí) · ↗ vzlet · ↘ přistání · P · Doba (záhlaví časů a P na střed nad hodnotou, doba
  vpravo; šířky sloupců pevné, nezávislé na písmu záhlaví). Ostatní údaje (účel, způsob vzletu, úloha, POB, trasa, plátce,
  poznámka, u zrušeného důvod) jsou v **detailu** po kliknutí na řádek. Na monitoru věže je
  vidět celý den bez posouvání.
- Stejně i u **jiného dne** (3.6) – deník je jen širší (zabere i místo pásků).
- Ukončené od posledního přistání, pod nimi oddíl Zrušené (přeškrtnutý rejstřík).
  Patička: lety, přistání, doba. Celá posádka s funkcemi v popisku řádku.
- **Pořadí počtů ve všech třech tabulkách** (deník, oba souhrny; rozhodnuto 8. 10. 2026):
  počet letů · počet přistání (P) · doba; plachtařský souhrn přistání nemá.

### 3.4 Souhrny (pravý sloupec)
Svislý sloupec **karet**; každá karta je samostatný zdroj, přidávají se postupně (zatím jen
karty 1 a 2, počasí a další zdroje přijdou se svými moduly):
1. **Plachtařský provoz:** tabulka kluzáků a vlečných (vleky) – Letadlo · Lety · Doba (bez
   přistání, 8. 10. 2026); celkem dole v patičce jako u deníku, **dva řádky: kluzáky a vleky**.
2. **Motorový provoz:** tabulka letadel Letadlo · Lety · P · Doba, dole řádek Celkem.

   Číselné sloupce (Lety, P, Doba) jsou v obou tabulkách stejně široké – podle nejdelší doby
   „12°34″“ s odstupem; letadlo bere zbytek (8. 10. 2026).

   Souhrnné hodnoty jsou dole, ne nahoře (rozhodnuto 8. 10. 2026). Hlavička karty má jen
   název; rozpad podle startů a účelu ani sloupec „kde je“ není (kde letadlo je, ukazuje
   řada letadel).

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
- `GET /api/den` vrací navíc začátek ráno a konec večer nautického (`nr`, `nv`)
  a astronomického soumraku (`ar`, `av`) – prázdné, když nenastane.
- Kreslí se jako SVG s polohami v procentech (atributy), bez vložených stylů a pevných
  rozměrů; barvy z tokenů.

### 3.6 Jiný den
Šipky ‹ › v liště listují dny (dopředu nejvýš do dneška). Pod lištou modrý pruh „Prohlížíte
úterý 6. 10. 2026 · Zpět na dnešek“. Jiný den nemá pásky (ty patří jen k dnešku), deník je
širší (3.3), souhrny a časová osa jsou za vybraný den, řada letadel ukazuje dál
současný stav. Úpravy letů jiného dne stejně jako dnes (omezí je až uzávěrky). Rozhraní
`GET /api/lety?den=` a `GET /api/den?den=` už existuje.

### 3.7 Přihlášení jen ke čtení (pro klubovnu)
Viz 6.1. Na desktopu i na mobilu v relaci jen ke čtení: chybí „Nový let“ (i klávesa `N`
a adresa `/novy-let`), akce na páscích a v detailu, pole v detailu nejdou upravit, klik na
letadlo na zemi nic nezaloží, Můj provoz nejde měnit, záložky Osoby a Letadla nejsou.
Oranžový štítek „Jen ke čtení“: na desktopu v liště za názvem, na mobilu vpravo v řádku menu
(datum v hlavičce zůstává celé). V nabídce uživatele zůstává režim zobrazení a Odhlásit.

### 3.8 Detail letu a nový let – panel zprava
- Panely sahají od řady letadel **až dolů přes časovou osu** (víc místa, méně posouvání).
- **Detail** (620 px) vyjede zprava přes deník; pásky zůstanou vidět **a dál se ovládají** –
  věž může stisknout PŘISTÁL u jiného letu, aniž by detail zavírala. Obsah a pravidla úprav
  stejné jako na mobilu (`modul-lety.md` 3.5): pásek nahoře, bloky Posádka a let · Časy
  a místa · Platba a poznámka · Evidence s historií (u zrušeného i důvod zrušení). **Bez horní
  lišty s rejstříkem** (rozhodnuto 7. 10. 2026 – rejstřík je hned v pásku): pásek je úplně
  nahoře přes celou šířku panelu. **Zavírá se tlačítkem „Zavřít“ vpravo v patičce** (a `Esc`)
  – křížek vedle pásku zrušen 8. 10. 2026; stejně i panel nového letu.
  Úprava **na místě stejně jako na mobilu** – klik na pole otevře pod ním volby nebo pole
  k zápisu (stejné komponenty, jen menší). Akce v patičce.
- **Nový let** (820 px) je **jeden formulář místo průvodce** (rozhodnuto 7. 10. 2026): nahoře
  rozpracovaný pásek (čárkovaný, u aerovleku dvojice), vlevo Letadlo (dlaždice podle kategorií
  a stavu) · Účel a vzlet (segmenty) · Vlek; vpravo Posádka · Úloha (osnova → seznam) · Další
  údaje (místa, plátce, poznámka). Chybějící povinná volba má v hlavičce bloku „vyberte“
  a patička vypíše „Chybí: …“. Patička: VZLET TEĎ · NAPLÁNOVAT · PROBĚHLÝ LET… (ukáže pole časů).
  Pravidla a nabídky stejné jako průvodce; na mobilu průvodce zůstává.
  **Vybrané letadlo se sbalí** do jednoho řádku (kategorie, rejstřík a typ; klik = znovu
  dlaždice), aby se formulář vešel i na notebook 1366 × 768 (8. 10. 2026).
- **Otevřená volba se posune do zorného pole** (detail i nový let): po kliknutí v bloku se
  panel posune tak, aby byl blok celý vidět – Hledat…, úprava místa ani úloha se neotevře pod
  spodním okrajem (8. 10. 2026).
- **Osoby:** rychlá volba čipy podle oprávnění a mého provozu a „Hledat…“ (pole přímo v bloku,
  bez diakritiky) – stejná komponenta jako v průvodci.
- Adresy zůstávají (`/let/:id`, `/novy-let`): na desktopu otevřou panel nad deskou, na mobilu
  celou obrazovku – odkaz funguje na obou.

## 4. Technické řešení (frontend)

- **Stejné rozhraní (API) a data** – desktop nepotřebuje nové tabulky; souhrny provozu, „kde
  je“ a časová osa se počítají z letů dne. Jiný den používá `?den=` u `useDen` a `useLety`
  (`lety/api.ts`). Server navíc vrací nautický a astronomický soumrak (3.5).
- **Rozvržení** podle šířky okna (`rozvrzeni.ts`: `useDeska` od 1200 px, `useSirokaDeska` od
  1500 px; přepne se i při změně velikosti okna). `App.tsx` pak pro `/`, `/let/:id`
  a `/novy-let` vybere desku s panelem, jinak mobilní obrazovky; ostatní obrazovky (osoby,
  letadla, můj provoz) zatím zůstávají mobilní sloupcem uprostřed (krok 2 a 3 v kap. 5).
- **Sdílené s mobilem:** data a obnovování, akce letu a Zpět (`lety/akce.tsx`), detail
  rozdělený na bloky a akce (`DetailBloky`, `AkceDetailu` v `lety/Detail.tsx`), nový let jako
  stav s pravidly a bloky (`lety/novyLet.tsx` – průvodce je skládá po krocích, deska do
  formuláře), pořadí a dvojice vleku (`lety/poradi.ts`), štítky, volby, tlačítka.
- **Desktopové** (`deska/`): `Deska.tsx` (stránka, klávesy), `Lista.tsx`, `RadaLetadel.tsx`,
  `Pasky.tsx` a `PasekDeska.tsx` (pásek v řadě přihrádek), `DenikDne.tsx`, `Souhrny.tsx`,
  `CasovaOsa.tsx`, `PanelDetailu.tsx`, `PanelNovehoLetu.tsx`; `komponenty/Panel.tsx`.
- Styly dál jen z tokenů a **každá vlastnost jednou** (pravidlo 14, sjednoceno 8. 10. 2026):
  stav letu → výplň a barva jen v `lety/PanelLetu.css` (pásek mobilu, pásek desky, dlaždice
  letadla, proužek v řadě letadel); karty jen `Blok` / `.karta` (bloky, deník, souhrny, časová
  osa); záhlaví a patička tabulek jen `komponenty/Tabulka.css`; hlavní tlačítko `Tlacitko`;
  poloha nabídky uživatele a akce vedle sebe přes
  proměnné komponent; rozměry pro myš v `tokeny.css` (sada `.deska`). Desktopové komponenty
  mají vlastní CSS jen pro rozvržení.
- **Testy:** klikací testy `e2e/deska.spec.ts` v rozměru 1920 × 1080 a 1366 × 768: deska
  (pásky, řada letadel, deník, souhrny, časová osa), akce z pásku a Ctrl+Z, detail v panelu
  s úpravou a zároveň akce na jiném pásku, Esc, nový let klávesou N a z řady letadel až po
  VZLET TEĎ, souhrny za tlačítkem, jiný den bez pásků, pod 1200 px mobilní přehled.

## 5. Postup (malé moduly) – odsouhlaseno 7. 10. 2026

1. **Provozní deska** – vše v kap. 3 kromě 3.7 a počasí. (Tento návrh.)
2. ~~Osoby a Letadla na desktopu~~ – zrušeno 8. 10. 2026: desktop je jedna stránka, správa
   osob a letadel jen na mobilu.
3. **Můj provoz na desktopu** – v nabídce uživatele (malá úprava; jako panel, ne stránka).
4. **Počasí** – zdroj, stanice, mezipaměť na serveru (vlastní návrh).
5. **Přihlášení jen ke čtení** (6.1) – rozhodnuto 8. 10. 2026, dělá se hned po desce.
6. Později: deník za období (účetní), uzávěrky, export, velký displej.

## 6. Rozhodnutí a otázky

**Rozhodnuto 7. 10. 2026:** pásky se nepřetahují; jiný den ano (3.6); nový let jako jeden
formulář; postup podle kap. 5; zobrazovat maximum informací (řada letadel, časová osa); souhrn zvlášť pro plachtařský a motorový provoz (P = počet přistání, doba letů,
u plachtařů doba vleků, tabulka letadel Doba · P; bez počtu letů, rozpadu, sloupce „kde je“
a textu v hlavičce), TMG do motorového provozu, bez karty Piloti dnes; deník jeden řádek na let, zbytek
v detailu; pásek bez „⋯“; klidnější deska (na pásku žádné barevné písmo kromě tlačítek PŘISTÁL a VZLET, T&G bílé
s černým textem i na mobilu, detail bez lišty s rejstříkem, neutrální řada
letadel s proužkem stavu, trasa jen mimo moje letiště, výrazný vybraný pásek, jemnější osa,
panely až dolů); časová osa podle dne s pásmy soumraku. 8. 10. 2026: přihlášení jen ke čtení ano (6.1).

### 6.1 Přihlášení jen ke čtení – rozhodnuto 8. 10. 2026
Problém: na sdíleném počítači (klubovna) platí přihlášení 30 dní a kolemjdoucí by jednal pod
cizím jménem – audit by zapsal nesprávnou osobu.

- U přihlášení zaškrtávátko **„Jen ke čtení (sdílený počítač)“**. Je to vlastnost **relace**
  (zařízení), ne účtu (`db/030`):
  ```sql
  ALTER TABLE lkkl.relace ADD COLUMN jen_cteni boolean NOT NULL DEFAULT false;
  ```
  Bez auditu (relace audit nemají); přihlášení se zapisuje jako dosud.
- **Hlídá server:** v relaci jen ke čtení odmítne závislost `prihlaseny` každý požadavek
  kromě čtení (`GET`) hláškou 403 „Přihlášeno jen ke čtení…“ – jedna kontrola pro všechny
  endpointy; test projde všechny zápisy aplikace, že žádný kontrolu neobejde. Odhlásit se
  jde vždy. Skrytí ovládání v aplikaci (3.7) je jen pohodlí.
- **Bez práv:** v relaci jen ke čtení se práva (admin, správa osob a letadel…) neuplatní,
  `GET /api/ja` je vrátí vypnutá a s příznakem `jen_cteni`.
- Relace jen ke čtení platí 30 dní jako ostatní (počítač v klubovně zůstane přihlášený).
- **Nejsou** (rozhodnuto 8. 10. 2026, zatím ne): tlačítko „Přihlásit k úpravám“ – kdo chce
  zapisovat, odhlásí se a přihlásí se znovu bez zaškrtnutí; ani **Můj provoz** se v relaci jen
  ke čtení nemění (je to také zápis).

### 6.2 Další otázky
1. **Písmo 12 / 15 / 20 px i na desktopu.** Na věži z dálky stačí zvětšení prohlížeče
   (`Ctrl +`); rozvržení s ním počítá (1920 při 125 % = 1536 px, souhrny zůstanou).
   Čtvrtou velikost (např. hodiny) zatím nezavádím.
2. **Počasí – zdroj.** Kandidát: veřejné API `aviationweather.gov` (METAR/TAF ve formátu JSON,
   bez klíče), stahuje server a drží 5–10 minut v paměti (žádná tabulka, nejde o naše data);
   stanice jako číselník nebo příznak u letiště. Rozhodne se v modulu Počasí.
