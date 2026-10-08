# Modul: lety (první fungující část aplikace)

> **NÁVRH ke schválení.** Po schválení se podle něj napíše kód; změny nejdřív sem.

Vzhled podle maket `docs/navrhy/lety-mobil-v4.html` (přehled a detail; pásek podle
`pasek-mobil-v5.html`) a
`docs/navrhy/pruvodce-mobil-v4.html` (nový let) – mobil, světlý i tmavý režim. Data v tabulkách
`let`, `posadka`, `let_tg` a pohledech `v_let`, `v_historie_letu`, `v_lov_letadlo`,
`v_lov_*` (skripty `db/009`–`015`). Obrazovka pro počítač (provozní deska): `docs/modul-desktop.md`.

## 1. Rozsah

**Ano:**
- **Přihlašovací obrazovka** (e-mail a heslo, nastavení hesla odkazem) – bez ní se do aplikace
  nedostaneme; rozhraní už existuje (`docs/modul-prihlasovani.md`).
- **Přehled letů dne:** hlavička (UTC, den, TB/SR/SS/TE), sekce ve vzduchu / naplánované /
  ukončené / zrušené, pásky podle makety, varování (po konci soumraku, přes maximální dobu),
  sbalování sekcí, režim zobrazení.
- **Průvodce novým letem:** letadlo → posádka → let; VZLET TEĎ / Naplánovat / Proběhlý let;
  vlek jako dvojice letů.
- **Akce letu:** VZLET (u vleku pro oba lety), PŘISTÁL, T&G, **Zpět** po akci, zrušení
  s důvodem, obnovení.
- **Detail letu:** všechny údaje, úprava ťuknutím na místě, historie z auditu.

**Ne (později):** úlohy z osnov (blok úlohy bude, až dodáte osnovy – do té doby jen obecné
úlohy, viz otázka 6), uzávěrky, výpis a export, můj nálet, displej, upozornění (e-mail, push),
kontrola dokladů a rozlétanosti (obrazovka pro počítač je samostatný modul `docs/modul-desktop.md`).

## 2. Rozhraní (API)

Vše pod `/api`, přihlášený uživatel, data JSON. Čas „teď“ vždy ze serveru (databáze).

| Metoda a adresa | Co dělá |
|---|---|
| `GET /api/den?den=RRRR-MM-DD` | den do hlavičky: datum, čas serveru, domovské letiště, sluneční časy (TB, SR, SS, TE) |
| `GET /api/lety?den=RRRR-MM-DD` | lety dne pro pásky (z `v_let` + posádka, počet T&G, varování) a čas serveru; dnes i vše, co je ve vzduchu |
| `GET /api/lety/nabidky` | vše pro průvodce: letadla (`v_lov_letadlo` + stav letí / naplánován), účely, způsoby vzletu, osoby s rolemi, které smí zastat (`v_osoba_smi`), obecné úlohy |
| `GET /api/lety/nabidka-osob?letadlo_id=` | naposledy létající na letadle (rychlá volba) a poslední vlekař vlečné |
| `POST /api/lety` | nový let z průvodce: letadlo, účel, posádka, POB, způsob vzletu, vlek (vlečná + vlekař), plátce, úloha, akce `vzlet` / `naplanovat` / `probehly` (s časy a počtem přistání) |
| `GET /api/lety/{id}` | detail letu včetně historie (`v_historie_letu`) |
| `POST /api/lety/{id}` | úprava údajů z detailu (jen změněná pole + číslo verze) |
| `POST /api/lety/{id}/vzlet` | vzlet teď (u vleku oba lety najednou) |
| `POST /api/lety/{id}/pristani` | přistání teď; místo = domovské, není-li zadáno; počet přistání = T&G + 1 |
| `POST /api/lety/{id}/tg` | T&G teď (jen motorová, TMG, UL; vlečná tlačítko T&G nemá – při vleku se nedělá) |
| `POST /api/lety/{id}/zpet` | vrátí poslední akci (vzlet, přistání, T&G) – viz 3.4 |
| `POST /api/lety/{id}/zrusit` | zrušení s důvodem (`lov_duvod_zruseni`) |
| `POST /api/lety/{id}/obnovit` | zrušení se vrátí |

## 3. Chování

### 3.1 Pravidla
Pravidla, která hlídá databáze (jeden PIC, funkce podle účelu, POB, vlek, překryv letů,
T&G, nemazání, doplnění domovského letiště), server neopakuje – chybu z databáze převede na
srozumitelnou hlášku. Server navíc: **plátce** předvyplní podle účelu (normální → PIC, výcvik
a sólo → žák, přezkoušení → přezkoušený), **vlek** založí jako dva propojené lety v jedné
transakci (vlečný let bez účelu, plátce = plátce kluzáku).

**Proběhlý aerovlek** se zadává i s časem přistání vlečné (vlečný let je samostatný let
s vlastní dobou); vzlet je u obou stejný. **Vlekař** nemůže být zároveň v posádce kluzáku
(předvyplní se vlekař posledního vleku vlečné, jen když v posádce není).

**Osoba na palubě** (PIC, žák, přezkoušený) nemůže být ve vzduchu ve dvou letech zároveň –
hlídá databáze při vzletu, proběhlém letu i úpravě časů a posádky (`db/018`); plánovat jde
volně, dozor na zemi se nepočítá. **Vlek** je dvojitý pásek, dokud je naplánovaný nebo
ve vzduchu; jednotlivě (po přistání vlečné) má vlečná účel „vlek“. Ťuknutí na polovinu
dvojice otevře detail jejího letu.

**Vzhled přehledu** (návrh v4, odsouhlaseno 7. 10. 2026, nahrazuje štítky z 6. 10.):
- **Ve vzduchu a naplánované = pásek** jako papírový strip: barevný panel podle stavu (zelený
  ve vzduchu, modrý naplánovaný, červený problém) s výrazným okrajem (ve světlém režimu téměř
  černým, v tmavém světle šedým): rejstřík a typ · posádka (**každá osoba na vlastním
  řádku**) · vpravo čas (stopky a čas vzletu se šikmou šipkou ↗) · dole **štítky v pevných pozicích** účel ·
  způsob vzletu · POB · úloha (maketa `pasek-mobil-v5.html`, 7. 10. 2026). Každý typ má stálé
  místo a šířku podle nejdelšího textu; chybí-li údaj, místo zůstane prázdné a nic se
  neposune. Běžné hodnoty se nevypisují: účel „normální“ a způsob vzletu „vlastní“ (ten
  aplikace sama přiřadí každému letu, který není kluzák – i vlečné). U ukončeného letu
  (pásek nahoře v detailu) je vpravo v řádku štítků doba tučně a počet přistání („3×“).
  Varování má v pásku vlastní červený řádek. Akce pod páskem (T&G a PŘISTÁL, u naplánovaného
  VZLET přes celou šířku). **Barvy písma a tlačítek** (sjednoceno s desktopem 7. 10. 2026):
  stopky v barvě textu (stav říká výplň pásku); PŘISTÁL zelené a VZLET modré plné s bílým
  textem; T&G bílé s černým textem (pásek i detail).
- **Šipky u časů** (8. 10. 2026, mobil i desktop): vzlet šikmo nahoru ↗, přistání šikmo dolů ↘,
  kreslené (komponenta `Sipka`) – výraznější než znak písma a na každém zařízení stejné.
- **Ukončené a zrušené = deník**: řádky v jedné kartě, sloupce Letadlo · Posádka · Čas (vzlet
  nad přistáním) · Doba · P (počet přistání). **První dva řádky** patří posádce (osoba na
  řádek; je-li jen jedna, druhý zůstane prázdný), **třetí řádek** šedě vždy POB a odchylky od
  běžného letu (účel, způsob vzletu, úloha, dodatečně; u zrušeného důvod) – od posádky až do konce
  řádku, bez zalomení (7. 10. 2026).
- **Letiště** vzletu a přistání se v přehledu neukazují, jen v detailu letu.
- Šířky pozic štítků a sloupců deníku (tokeny `--mista-stitku`, `--sloupce-deniku`) jsou ve
  znacích písma s rezervou pro nejdelší text i širší písmo telefonu; čas vpravo pobere i
  stopky přes 10 hodin.

**Průvodce:** nahoře ukazatel postupu (tři díly) a od kroku 2 **rozpracovaný pásek** letu
(čárkovaný okraj = ještě neuložený), který se plní s každou volbou. Krok 1: dlaždice letadel
ve skupinách podle kategorie (barva podle stavu jako v přehledu), všechny stejně vysoké – tři
řádky: rejstřík · typ · stav (mimo provoz, letí, naplánován; jinak prázdný); „vlečná“ se
neuvádí, soukromé letadlo má bílou dlaždici a **světle šedý** rejstřík (8. 10. 2026; tlumená
šedá `--barva-seda-svetla`, běžná šedá se od černé málo lišila). Volby v blocích (karta
s hlavičkou): účel, způsob vzletu a den jako **segmenty** v jednom řádku, osoby jako **čipy**
(„Hledat…“ otevře hledání podle jména; po výběru zůstane jen vybraná osoba plně modře
a „Hledat…“, ťuknutím na ni se nabídka znovu otevře – stejně u vlekaře), chybějící povinná volba má
v hlavičce bloku „vyberte“. Úloha: osnova, pak seznam úloh „kód · název“. **Místo vzletu**,
**místo přistání** a **plátce** jsou předvyplněné řádky v bloku Další údaje (místa = moje
letiště), ťuknutím se změní (místo: hledání letiště nebo popis místa); u aerovleku platí
místo přistání pro kluzák i vlečnou. Proběhlý let: časy vzletu,
přistání (a přistání vlečné) vedle sebe, aktivní zvýrazněný, pod ním mřížka hodin a minut,
−1 / +1 a doba letu.
**Nabídka osob podle oprávnění** (db/021, 022, 024; model `docs/navrh-opravneni.md`):
oprávnění osoby (FI(S), FE(S), vlekař…) opravňuje k **rolím v letu** (`lov_role`: instruktor =
výcvik · PIC, dozor = sólo · dozor, examinátor = přezkoušení · PIC, vlekař = vlečný let · PIC)
na kategoriích letadel, pro které ho osoba má. Přezkoušení jen examinátoři, výcvik a dozor
instruktoři (i omezení). V rychlé volbě každého
pole posádky (i vlekaře) se nabídnou osoby, které danou roli smí zastat na kategorii
vybraného letadla; nesmí-li nikdo, nabídne se Já a naposledy létající. „Hledat…“ vždy hledá
mezi všemi (výjimky). Nic se nekontroluje ani neblokuje, platnost oprávnění se neeviduje.
Oprávnění osob zadává správce v aplikaci (Osoby → detail), role oprávnění v databázi
(`lov_opravneni_role`; kontrola v `v_osoba_opravneni`).
**Zrušení vleku:** naplánovaný vlek se ruší celý, po vzletu jen zvolený let (kluzák po
přetrženém laně – vlečná letí dál).

### 3.2 Souběh (víc lidí najednou)
- **Stisk platí jen jednou:** VZLET u letadla, které už vzlétlo, vrátí 409 a zprávu
  „Už vzlétl v 12:05:13 (Eva Časoměřič)“ (kdo a kdy z auditu); stejně PŘISTÁL.
- **Úprava v detailu** nese číslo verze; změnil-li let mezitím někdo jiný, server ji odmítne
  a obrazovka ukáže aktuální stav.
- **Nová verze aplikace:** otevřená aplikace se jednou za minutu ptá na verzi serveru; po
  nasazení ukáže pruh „Je k dispozici nová verze aplikace · Načíst“.
- **Přehled se obnovuje sám** (dotaz každých 10 s a hned po návratu do aplikace nebo
  odemčení telefonu), aby pilot i časoměřič viděli totéž.

### 3.3 Varování na páscích
- **Po konci občanského soumraku** (TE) a stále ve vzduchu → červený pásek s důvodem.
- **Přes maximální dobu letu** letadla → totéž.
- Sluneční časy počítá server pro souřadnice domovského letiště (knihovna `astral`).

### 3.4 Zpět
Po VZLET, PŘISTÁL a T&G se na 6 s ukáže lišta „OK-CWF přistání 12:44:31 · ZPĚT“. Zpět vrátí
let do stavu před akcí (vzlet → naplánovaný, přistání → ve vzduchu, T&G → bez posledního
času). V auditu zůstane obojí (akce i návrat).

### 3.5 Detail letu
Nahoře **stejný pásek jako v přehledu** (bez akcí), pod ním bloky Posádka a let · Časy a místa
(UTC) · Platba a poznámka · Evidence. Údaje jsou **pole ve dvou sloupcích** (popisek nad
hodnotou, přepážky jako na pásku); upravitelné pole má vpravo „›“ a ťuknutím se pod ním
otevře úprava (výběr z nabídky, čas stejným výběrem jako u proběhlého letu). Historie
z `v_historie_letu` je v Evidenci sbalená („3 úpravy“), ťuknutím se rozbalí. Akce dole
(u ukončeného letu „Zrušit let“; „Další let odsud“ zrušen 7. 10. 2026).

Upravit jde: posádka (jiná osoba ve funkci), POB (je-li zadaný), úloha, místo a čas vzletu,
**místo přistání vždy** (do přistání plán, pak skutečnost; letiště, nebo popis místa
v terénu), po přistání čas přistání a přistání celkem,
plátce a poznámka. **Neupravuje se** letadlo, účel ani způsob vzletu –
takový let se zruší s důvodem „Založeno omylem“ a založí znovu (mění se s nimi pravidla
posádky, úlohy i vleku). Zrušení a obnovení vleku platí pro oba lety dvojice. Zrušený let
nejde upravit, jen obnovit.

## 4. Frontend

- **React + TypeScript**, sestavení **Vite**; data **TanStack Query** (obnovování, opakování
  při výpadku sítě); adresy **react-router**.
- **Bez knihovny komponent.** Vlastní komponenty podle makety, styly podle pravidla
  normalizace: `styly/tokeny.css` (jediné místo s pevnými hodnotami, převzaté z makety),
  komponenty každá se svým CSS jen z tokenů. **stylelint** před commitem odmítne pevnou barvu
  nebo rozměr mimo tokeny.
- Komponenty: hlavička, menu, sekce, pásek letu (varianty stavu, `lety/Pasek.tsx`), deník,
  blok s poli (`lety/Udaje.tsx`), volby – segmenty, čipy osob, seznam úloh, počet
  (`lety/Volby.tsx`), výběr času (`lety/VyberCasu.tsx`), dlaždice letadla, štítek, tlačítko,
  oznámení Zpět, obrazovka s bloky (průvodce, detail).
- **Provoz:** server FastAPI vrací i sestavený frontend (jedna adresa); při vývoji Vite
  s přesměrováním `/api` na server.

```
frontend/
  src/
    styly/tokeny.css, zaklad.css
    komponenty/…            jedna komponenta = .tsx + .css
    stranky/Prihlaseni.tsx, Lety.tsx
    lety/Pruvodce.tsx, Detail.tsx, api.ts
```

## 5. Testy

- **Server (pytest):** každý endpoint a pravidlo – vytvoření letu všemi akcemi, vlek (dvojice,
  společný vzlet), idempotence vzletu a přistání, Zpět, zrušení a obnovení, úprava s verzí,
  varování soumrak / max. doba, historie v detailu.
- **Klikací testy (Playwright, rozměr mobilu):** přihlášení a nastavení hesla; přehled (pásky,
  deník); průvodce → VZLET TEĎ → T&G → PŘISTÁL → Zpět; aerovlek; proběhlý let (i aerovlek
  odjinud); úprava v detailu (posádka, úloha, místa, časy, plátce, zrušení, obnovení, další
  let); pruh nové verze, režim zobrazení. Běží i na GitHubu (CI) při každém commitu. Před čekáním na prvek po přechodu
  vždy ověřit nadpis nové obrazovky.

## 6. Rozhodnutí (6. 10. 2026)

1. **Kdo smí co:** každý přihlášený smí zakládat lety, ovládat je, upravovat i rušit; omezení
   přijdou s uzávěrkami.
2. **Zpět** jen 6 s po akci (lišta), ne později.
3. **Krátký let do 1 minuty:** doba letu se zapisuje nejméně jako 1 minuta (`db/020`). PŘISTÁL
   u letu kratšího než minuta se zeptá: **počítat** (1 minuta), nebo **zrušit** jako přerušený
   vzlet. Přepínač „start bez doby“ (`doba_nulova`) zrušen.
4. **Obnovování přehledu** každých 10 s.
5. **Fáze testování 1** na serveru – nejdřív se rozchodí standardní nasazení (samostatný
   návrh `docs/nasazeni.md`).
6. **Osnovy a úlohy** založené (`db/016`); úloha je u výcviku, sóla a přezkoušení povinná,
   jen když pro účel a kategorii letadla nějaká existuje (`db/019`). Kluzáky: osnovy IU, IA
   a II z Programu výcviku AeČR v.6 (úprava AK Kladno), nabídka úlohy podle účelu (vazba
   úloha ↔ účel); TMG zatím ne. Obecné úlohy u kluzáků nahradil sportovní výcvik (II).
7. **Nedostupný server** (7. 10. 2026): výpadek sítě → „Nepodařilo se spojit se serverem…“;
   server neběží a odpoví proxy (502, 503, 504) → „Server je nedostupný (možná se právě
   aktualizuje). Zkuste to za chvíli.“ Přehled letů při neúspěšném obnovení ukazuje „Bez
   spojení se serverem – údaje z … UTC“.

8. **Místa vzletu a přistání** (7. 10. 2026, `db/027`, maketa
   `docs/navrhy/mista-letu-mobil.html`): obě místa jsou nepovinná a má je každý let **od
   založení** – nezadané = výchozí letiště (moje letiště z mého provozu, jinak domovské;
   databáze doplní domovské u zápisu přímo v databázi). Místo přistání je do přistání
   **plán**, po přistání skutečnost; obě místa jdou upravit u naplánovaného, letícího
   i ukončeného letu. Přistání z pásku místo nemění (přistání do terénu se opraví v detailu,
   plán zůstane v historii letu). Zpět u přistání místo nechá. Aerovlek: místo přistání
   v průvodci platí pro kluzák i vlečnou (spolu se vrací, nebo spolu přeletí), v detailu má
   každý let své. Stávající lety
   bez místa přistání dostaly domovské (převod bez zápisu do historie).
9. **Trasa na pásku** (varianta B): u naplánovaného letu a letu ve vzduchu štítek vpravo
   v řádku štítků, jen jedna strana – kam letí („→ LKMB“), jinak odkud („LKMB →“); jen když
   místo není moje letiště. Dlouhý popis místa se zkrátí („→ pole …“). Ukončený let trasu
   nemá (vpravo doba letu).
10. **Rychlá volba letišť** (7. 10. 2026, `db/028`): při výběru místa (průvodce, detail, letiště
    pro dnešek) se hned nabízí jen letiště s příznakem `lov_letiste.rychla_volba` (domovské,
    LKPC, LKSZ, LKCH, LKRK, LKHV, LKPS – mění správce v databázi) a moje letiště; ostatní
    najde „Hledat…“ podle kódu nebo názvu bez diakritiky.
