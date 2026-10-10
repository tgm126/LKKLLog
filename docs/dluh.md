# Technický dluh a odložené body

Co víme, že by šlo udělat lépe, ale záměrně to neděláme hned. Pravidlo: **při dalším zásahu
do daného souboru** se příslušný bod udělá s ním (ne jako samostatný úkol). Položka se
po vyřešení maže. Původ: nezávislý code review z 9. 10. 2026 (zpracován 9.–10. 10. 2026,
nasazeno v2.24.0–v2.24.2); body, které se udělaly, tu nejsou.

## Při dalším zásahu do souboru

| Soubor | Co | Proč odloženo |
|---|---|---|
| `backend/app/prihlasovani.py` (~700 ř.) | rozdělit: `relace.py` (relace, cookie, závislosti), `ucty.py` (správa účtů, pozvánky, e-mailová šablona), „přihlásit se jako“ | jen čitelnost; bez změny chování |
| `backend/app/lety.py` (~900 ř.) | rozdělit: `slunce.py` (sluneční výpočty), `lety_akce.py` (vzlet, přistání, T&G, zpět), přehled dne, průvodce a detail zvlášť | tamtéž |
| `frontend/src/lety/Pasek.tsx` + `deska/PasekDeska.tsx` | dvě `CasLetu`, dvojí markup „typ · vlečná“ a CSS `.let-stopky`/`.pasek-stopky`, `.let-varovani`/`.pasek-varovani` → společné přihrádky (`Rejstrik`, `CasLetu`, `Varovani`) s jednou třídou; mobil a deska skládají jen mřížku | změna vzhledu obou podob – dělat při příští úpravě pásku se snímky (skill snimky-mobil) |
| `frontend/src/vycvik/Editor.tsx` (~940 ř., 14 komponent) | rozdělit na `Osnovy.tsx`, `Typy.tsx`, `prvky.tsx`, `Nahled.tsx` | čitelnost |
| `frontend/src/lety/novyLet.tsx` (~770 ř.) | `useNovyLet` rozdělit na čistou funkci `odvodit(novy, nabidky)` + tenký hook (dnes vrací ~30 položek); čistou funkci pokrýt jednotkovými testy (vitest) | větší zásah do průvodce; dnes pokryto jen klikacími testy |
| `frontend/src/lety/Detail.tsx` (~540 ř.) | `AkceDetailu.tsx`, `Upravy.tsx` | čitelnost |
| `frontend/src/{provoz,osoby,sprava,vycvik}/api.ts` | čtyři kopie `useMutation + oznamit` → jedna pomůcka `useMutaceApi` | drobné |
| `frontend/src/deska/{RadaLetadel,Souhrny,CasovaOsa}.tsx` | vazba lety ↔ letadla přes text `rejstrik` místo `letadlo_id` | funguje (rejstřík je jedinečný); změnit při úpravě desky |
| `frontend/src/komponenty/Dialog.tsx` | na desce je dialog mobilní „bottom sheet“ 480 px i na 1920 px – desktopová podoba (uprostřed, u kurzoru) | návrh desktopu (docs/modul-desktop.md) zatím dialog neřeší |
| `frontend/src/deska/PanelDetailu.tsx` | komentář v hlavičce popisuje starší podobu (křížek vedle pásku) | opravit při příštím zásahu |

## Vědomě neprovedeno (s důvodem)

- **Kontrola typů Pythonu (pyright/ty):** nad `backend/app` hlásí ~217 chyb, téměř vše typování
  řádků psycopg (`row["id"]` nad `tuple`, skládané dotazy nejsou `LiteralString`). Vyplatí se
  až s typovaným spojením (`Connection[DictRow]`) napříč kódem – samostatný úkol, ne hned.
- **Klikací testy jen v Chromiu** (`playwright.config.ts`, Pixel 7): WebKit na runneru
  potřebuje systémové balíčky (`--with-deps`, pomalé zrcadlo Ubuntu – viz komentář v `ci.yml`).
  iPhone se zkouší ručně; přidat projekt WebKit pro `lety`, `akce`, `prihlaseni`, až bude
  instalace v CI rychlá.
- **Jeden balíček frontendu** (~415 kB, 124 kB gzip) bez `lazy()` pro `vycvik/`, `osoby/`,
  `sprava/`: soubory s otiskem v názvu se cachují rok (`Cache-Control: immutable`), pro klub
  je to jedno načtení. Rozdělit, až balíček přeroste ~1 MB.
- **Manifest `standalone` bez service workeru:** offline aplikace nefunguje – záměr, data musí
  být vždy ze serveru (souběh víc lidí). Nedělat.
- **Indexy** pro dotaz podle dne (`(coalesce(cas_vzletu, zalozeno) AT TIME ZONE 'UTC')::date`,
  `backend/app/lety.py`) a pro LATERAL polohy letadla (`db/037`): při tisících letů ročně
  nepostřehnutelné. Přidat, až `EXPLAIN` nad serverovými daty ukáže sekvenční čtení v řádu
  desítek ms.
- **502 u odeslání e-mailu nese text chyby SMTP** (`prihlasovani.py`, `ucet_pozvanka_emailem`):
  vidí ho jen admin a hodí se k diagnostice; text je i v `lkkl.email.chyba`. Nechat.
- **Souběh u pravidel přes více řádků** – přijato, zapsáno v `docs/modul-lety.md` 3.2.
- **Role databáze** (aplikace jako vlastník schématu) – rozhodnuto, zapsáno v
  `docs/nasazeni.md` (kap. Role databáze).
- **Zablokování účtu zvenčí** – přijato, zapsáno v `docs/modul-prihlasovani.md` 4.1.

## K rozhodnutí uživatele (design)

- **12px šedý text na slunci:** funkce v posádce, typ letadla, štítky a drobný text deníku jsou
  na mobilu na přímém slunci nejhůř čitelný prvek pásku. Možnost: 12 px nechat jen nadpisům
  sekcí a štítkům, ostatní 15 px (rozšíří pásek o řádek). Zatím beze změny – vyzkoušet venku.
