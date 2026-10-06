# Modul: lety (první fungující část aplikace)

> **NÁVRH ke schválení.** Po schválení se podle něj napíše kód; změny nejdřív sem.

Vzhled a chování podle makety `docs/navrhy/lety-mobil.html` (mobil). Data v tabulkách
`let`, `posadka`, `let_tg` a pohledech `v_let`, `v_historie_letu`, `v_letadlo_nabidka`,
`v_lov_*` (skripty `db/009`–`015`). Obrazovka pro počítač zatím ne.

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
  s důvodem, obnovení, další let odsud.
- **Detail letu:** všechny údaje, úprava ťuknutím na místě, historie z auditu.

**Ne (později):** úlohy z osnov (blok úlohy bude, až dodáte osnovy – do té doby jen obecné
úlohy, viz otázka 6), uzávěrky, výpis a export, můj nálet, displej, upozornění (e-mail, push),
obrazovka pro počítač, kontrola dokladů a rozlétanosti.

## 2. Rozhraní (API)

Vše pod `/api`, přihlášený uživatel, data JSON. Čas „teď“ vždy ze serveru (databáze).

| Metoda a adresa | Co dělá |
|---|---|
| `GET /api/lety?den=RRRR-MM-DD` | lety dne pro pásky (z `v_let` + posádka, počet T&G, varování) a sluneční časy dne (TB, SR, SS, TE pro domovské letiště) |
| `GET /api/lety/nabidky` | vše pro průvodce: letadla (`v_letadlo_nabidka` + stav letí / naplánován), účely, způsoby vzletu, osoby, vlekaři, obecné úlohy |
| `GET /api/lety/nabidka-osob?letadlo_id=` | naposledy létající na letadle (rychlá volba) a poslední vlekař vlečné |
| `POST /api/lety` | nový let z průvodce: letadlo, účel, posádka, POB, způsob vzletu, vlek (vlečná + vlekař), plátce, úloha, akce `vzlet` / `naplanovat` / `probehly` (s časy a počtem přistání) |
| `GET /api/lety/{id}` | detail letu včetně historie (`v_historie_letu`) |
| `POST /api/lety/{id}` | úprava údajů z detailu (jen změněná pole + číslo verze) |
| `POST /api/lety/{id}/vzlet` | vzlet teď (u vleku oba lety najednou) |
| `POST /api/lety/{id}/pristani` | přistání teď; místo = domovské, není-li zadáno; počet přistání = T&G + 1 |
| `POST /api/lety/{id}/tg` | T&G teď (jen motorová, TMG, UL) |
| `POST /api/lety/{id}/zpet` | vrátí poslední akci (vzlet, přistání, T&G) – viz 3.4 |
| `POST /api/lety/{id}/zrusit` | zrušení s důvodem (`lov_duvod_zruseni`) |
| `POST /api/lety/{id}/obnovit` | zrušení se vrátí |
| `POST /api/lety/{id}/dalsi` | další let odsud: stejné letadlo, účel, posádka; místo vzletu = místo přistání |

## 3. Chování

### 3.1 Pravidla
Pravidla, která hlídá databáze (jeden PIC, funkce podle účelu, POB, vlek, překryv letů,
T&G, nemazání, doplnění domovského letiště), server neopakuje – chybu z databáze převede na
srozumitelnou hlášku. Server navíc: **plátce** předvyplní podle účelu (normální → PIC, výcvik
a sólo → žák, přezkoušení → přezkoušený), **vlek** založí jako dva propojené lety v jedné
transakci (vlečný let bez účelu, plátce = plátce kluzáku).

### 3.2 Souběh (víc lidí najednou)
- **Stisk platí jen jednou:** VZLET u letadla, které už vzlétlo, vrátí 409 a zprávu
  „Už vzlétl v 12:05:13 (Eva Časoměřič)“ (kdo a kdy z auditu); stejně PŘISTÁL.
- **Úprava v detailu** nese číslo verze; změnil-li let mezitím někdo jiný, server ji odmítne
  a obrazovka ukáže aktuální stav.
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
Údaje v blocích Posádka · Let · Časy a místa · Platba · Poznámka · Evidence. Ťuknutí na údaj
ho upraví na místě (výběr z nabídky, čas stejným výběrem jako u proběhlého letu). Evidence
ukazuje historii z `v_historie_letu`.

## 4. Frontend

- **React + TypeScript**, sestavení **Vite**; data **TanStack Query** (obnovování, opakování
  při výpadku sítě); adresy **react-router**.
- **Bez knihovny komponent.** Vlastní komponenty podle makety, styly podle pravidla
  normalizace: `styly/tokeny.css` (jediné místo s pevnými hodnotami, převzaté z makety),
  komponenty každá se svým CSS jen z tokenů. **stylelint** před commitem odmítne pevnou barvu
  nebo rozměr mimo tokeny.
- Komponenty: hlavička, menu, sekce, pásek letu (varianty stavu), štítek, tlačítko, dlaždice
  letadla, rychlá volba osoby, volba počtu, výběr času, oznámení Zpět, obrazovka (průvodce,
  detail).
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
- **Klikací testy (Playwright, rozměr mobilu):** přihlášení; průvodce → VZLET TEĎ → T&G →
  PŘISTÁL → Zpět; aerovlek; proběhlý let; úprava v detailu. Před čekáním na prvek po přechodu
  vždy ověřit nadpis nové obrazovky.

## 6. Rozhodnutí (6. 10. 2026)

1. **Kdo smí co:** každý přihlášený smí zakládat lety, ovládat je, upravovat i rušit; omezení
   přijdou s uzávěrkami.
2. **Zpět** jen 6 s po akci (lišta), ne později.
3. **Krátký let do 1 minuty:** zatím bez dotazu při přistání; v detailu přepínač „start bez
   doby“ (`doba_nulova`). Dotaz přidáme, ukáže-li ho praxe.
4. **Obnovování přehledu** každých 10 s.
5. **Fáze testování 1** na serveru – nejdřív se rozchodí standardní nasazení (samostatný
   návrh `docs/nasazeni.md`).
6. **Osnovy a úlohy** založené (`db/016`) s testovacími daty; úloha je u výcviku, sóla
   a přezkoušení povinná.
