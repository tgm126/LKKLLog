# Code review projektu LKKL Log (9. 10. 2026)

Nezávislé posouzení celého projektu (databáze `db/`, server `backend/`, frontend `frontend/`,
dokumentace `docs/`, nasazení) pohledem seniorního full stack vývojáře. Stav po commitu
`ef6d2d4` (skript 044). Každé zjištění je ověřené v kódu; odkazy jsou `soubor:řádek`.

Ověřený stav kontrol: `ruff check`, `ruff format`, `pytest` (104 testů, 33 s) i
`npm run kontrola` (tsc, eslint, stylelint) prošly bez chyby.

## 1. Shrnutí

| Oblast | Hodnocení | Jednou větou |
|---|---|---|
| Architektura | 8/10 | Logika a pravidla v databázi, tenký SQL server, dva oddělené designy obrazovek – přesně podle CLAUDE.md. |
| Databáze | 8/10 | Čistý normalizovaný model, obecný audit, jednotná platnost; chybí oddělení rolí a aktuální schéma se dá číst jen z živé DB. |
| Server (FastAPI) | 7/10 | Ukázněné transakce, parametrizace, relace a CSRF; jedna eskalace práv (pozvánka pro admina), SMTP bez ověření certifikátu. |
| Frontend a UX | 8/10 | Vzorná normalizace stylů a mobilní ovládání; chybí timeout požadavku a stav „načítám“, typy API ručně opsané, žádné jednotkové testy. |
| Struktura a čitelnost | 7/10 | Konzistentní české názvosloví, komentáře „proč“ s daty; tři soubory přes 700 řádků a duplicity (pásek, UPDATE, práva). |
| **Celkem** | **8/10** | Nadprůměrně čistý projekt na svůj rozsah; dluh je lokalizovaný a opravitelný bez změny návrhu. |

**Co opravit nejdřív (pořadí podle rizika):**

1. Pozvánka pro heslo admina bez kontroly práv – správce osob se může stát adminem (K1).
2. STARTTLS bez ověření certifikátu SMTP serveru (S1).
3. Timeout požadavku a stav načítání na telefonu (F1, F2).
4. Role databáze: aplikace nemá být vlastníkem schématu (D1).
5. Datové skripty `_data` zastaralé – novou databázi z repozitáře nelze naplnit (D2).

## 2. Architektura

### Silné stránky

- **Pravidla v databázi, server jen překládá.** Dvojice vleku, překryvy, „právě jeden PIC“,
  povinná úloha, souhrn dne – vše triggery, EXCLUDE a pohledy (`db/035`, `db/036`). Server
  mapuje výjimky psycopg na hlášky (`backend/app/lety.py:280`). Stejné pravidlo tak platí pro
  aplikaci i pro ruční zásah ve VPS Centru.
- **Audit je skutečně v databázi.** Každý požadavek nastaví `lkkl.osoba_id` přes
  `db.s_kontextem` a ve `finally` ho zruší (`backend/app/db.py:57-65`); test
  `test_kontext_po_pozadavku_zmizi` hlídá únik kontextu do poolu.
- **Dva designy, jeden stav.** `frontend/src/App.tsx:41-63` přepíná jiný strom komponent
  (deska s panely vs. mobilní obrazovky) nad stejnými adresami; sdílí se jen pravidla
  (`lety/novyLet.tsx`, `lety/akce.tsx`, `lety/poradi.ts`).
- **Jeden image, migrace před startem**, zdravotní kontrola s databází, tajemství jen
  z prostředí a v produkci vynucený `LKKL_TAJNY_KLIC` (`backend/app/nastaveni.py:75-78`).
- **Proces:** každý modul má návrh v `docs/modul-*.md`, příručka pro uživatele se mění se
  stejným commitem, skripty vysvětlují rozhodnutí s datem.

### Zjištění

- **A1 (důležité) Pět práv je opsáno na deseti místech.** `Prava`, `Prihlaseny`, `UcetIn`,
  `UcetZmenaIn`, `Ucet` (`backend/app/prihlasovani.py:29-139`), pět téměř shodných
  závislostí (`:242-269`), SQL `v_ucet`, frontend `Ja.prava` (`frontend/src/api.ts`). Nové
  právo = ~10 úprav. Doporučení: jeden seznam názvů práv, modely z něj odvozené, závislost
  továrnou `pravo("spravuje_osoby")`.
- **A2 (důležité) Typy odpovědí API jsou ručně opsané.** `frontend/src/lety/api.ts:7-275`,
  `osoby/api.ts`, `vycvik/api.ts` zrcadlí Pydantic modely; `detail()` a `nabidky()`
  (`backend/app/lety.py:455,713`) navíc vracejí nevalidovaný `dict` bez `response_model`.
  Drift se projeví až v prohlížeči. Doporučení: `response_model` všude a generovat typy
  z `/api/openapi.json` (`openapi-typescript`) v `npm run kontrola`.
- **A3 (důležité) Dvě velké „krabice“.** `prihlasovani.py` (739 ř.) míchá infrastrukturu
  relací, správu účtů, e-mailovou šablonu a „přihlásit se jako“; `lety.py` (907 ř.) sluneční
  výpočty, přehled dne, akce, průvodce i detail. Doporučení: `relace.py`, `ucty.py`,
  `slunce.py`, `lety_akce.py`.
- **A4 (drobné) Chybí kontrola typů Pythonu.** Frontend má `tsc` strict, backend jen ruff.
  Doporučení: `ty` nebo `pyright` do „Před commitem“ a CI.

## 3. Databáze

### Silné stránky

- Identity sloupce, všude `timestamptz`, umělý PK + přirozený UNIQUE (`lower(email)`
  `db/004_osoba.sql:21`), **žádné `ON DELETE CASCADE`**, žádný `SECURITY DEFINER`, všechny
  objekty kvalifikované `lkkl.`.
- Domény `lkkl.kod/nazev/poradi/platny` (`db/008:12-22`), EXCLUDE s `btree_gist` na překryv
  letadla (`db/009:69`), částečný unikátní index pro jediné domovské letiště (`db/003:19`),
  generovaný `doba_min`, jednořádková `nastaveni` s `CHECK (jediny)`.
- Odvozené hodnoty nikde neuložené (stav letu, POB, poloha letadla, popisy osnov) – pohledy.
- Jedna funkce `audit_zapsat` s diffem jen změněných sloupců (`db/012:42-77`), ochrana
  `BEFORE UPDATE/DELETE/TRUNCATE` auditu. Jeden parametrizovaný trigger `kontrola_platnosti`
  na 30+ cizích klíčích (`db/031:106-127`).
- Migrace: každý skript ve vlastní transakci, otisk SHA-256 s normalizací CRLF, změna
  provedeného skriptu = chyba (`backend/app/migrace.py:38,59-66`).

### Zjištění

- **D1 (důležité) Ochrany jsou jen „dohodou“ – aplikace běží jako vlastník schématu.**
  V `db/` není žádný `CREATE ROLE`/`GRANT`. Vlastník může `DISABLE TRIGGER` (skripty to
  samy dělají: `db/017:70`, `db/027:14`, `db/041:295`) a `let_nemazat` obejde
  `set_config('lkkl.mazani_letu_dne','ano')` (`db/033:12`). Doporučení: role `lkkllog_app`
  jen s DML a `USAGE`, vlastník zvlášť pro migrace; `smazat_lety_dne` jako `SECURITY DEFINER`
  s pevným `search_path`.
- **D2 (důležité) Skripty `_data` neodpovídají struktuře.** Spouštějí se ručně po všech
  strukturálních skriptech (hlavičky `db/021_opravneni_data.sql`, `db/041_prezkouseni_data.sql`),
  ale `db/001_letadla_data.sql:9` vkládá do `lov_typ` bez `kod` (NOT NULL od 008), `:24` do
  tabulky `lkkl.letadlo` (přejmenována v 017), `db/003_letiste_data.sql:6` používá sloupec
  `icao` (přejmenován v 008). `db/019_uloha_podle_ucelu_data.sql:33` vyžaduje `psql -1`, ale
  hlavička to neuvádí. Doporučení: buď `_data` udržovat a ověřovat v CI (nová DB = struktura +
  všechna `_data`), nebo je nahradit jedním `db/pocatecni_data.sql` vygenerovaným z databáze.
- **D3 (důležité) Souběh u pravidel přes více řádků.** Překryv osoby (`db/025:63-92`), vlek
  jako dvojice (`db/035:15-36`) a „právě jeden PIC“ (`db/041:200`) jsou odložené triggery
  v READ COMMITTED – dvě souběžné transakce projdou obě. Doporučení:
  `pg_advisory_xact_lock` na osobu/let na začátku kontroly, nebo riziko vědomě zapsat.
- **D4 (důležité) Aktuální schéma je čitelné jen z živé databáze.** `let_zkontrolovat` má
  sedm plných kopií (009, 011, 016, 019, 032, 035, 041), `v_let` devět, `audit_hodnota`
  sedm; k tomu řada mrtvých objektů (`provoz`, `zahajit_ostry_provoz`, `lov_osnova_ucel`,
  `doba_nulova`…). Odpovídá pravidlu „žádné záplaty“, ale CLAUDE.md bod 6 (sloučení před
  první migrací) už nenastane. Doporučení: v CI po migraci testovací DB vygenerovat
  `pg_dump --schema-only --schema=lkkl` do `docs/schema.sql` a hlídat, že odpovídá commitu.
- **D5 (drobné)** `audit_hodnota` tiše ztratí hodnotu po smazání cíle (`vlecny_let_id` →
  NULL → `string_agg` vynechá; `db/012:231-242`); doporučení `coalesce(..., '#' || hodnota)`.
- **D6 (drobné)** Audit chybí na `lov_opravneni_kategorie` a `lov_opravneni_role`, i když
  rozhodují, kdo smí být instruktor; `lov_prezkouseni_opravneni` audit má (`db/042:98-107`).
- **D7 (drobné)** Chybí index pro dotaz podle dne
  (`(coalesce(cas_vzletu, zalozeno) AT TIME ZONE 'UTC')::date`, `backend/app/lety.py:254,266`)
  a pro LATERAL polohy letadla (`db/037:14-20`). Při tisících letů ročně nepostřehnutelné.
- **D8 (drobné) migrace.py:** provedený skript, který z `db/` zmizel, se tiše ignoruje; bez
  `pg_advisory_lock` proti dvojímu startu kontejneru; tabulka `lkkl.migrace` vzniká v Pythonu
  (`migrace.py:22-26`), ne v SQL (bod 12 CLAUDE.md); vyžaduje PostgreSQL ≥ 17
  (`SET EXPRESSION`, `NULLS NOT DISTINCT`), což nikde není zapsáno.
- **D9 (drobné)** `kontrola_platnosti` chybí na `email.osoba_id/odeslal_id` (`db/038:10-12`) –
  odkaz pro heslo jde poslat neplatné osobě. `nastaveni` nemá ochranu proti `DELETE`.
- **D10 (drobné)** `db/zaloha.sh`: obnova do prázdné DB selže na `btree_gist` (je v `public`,
  `--schema=lkkl` ho nezahrne) – do hlavičky doplnit `CREATE EXTENSION`.

## 4. Server (FastAPI)

### Silné stránky

- Autocommit + `conn.transaction()` jen tam, kde to má být celé nebo vůbec; optimistické
  zamykání letu přes `verze` + `FOR UPDATE` (`backend/app/lety.py:867-873`).
- Parametrizace všude; jediné f-stringy skládají názvy sloupců z pevných Pydantic modelů
  (označeno `noqa: S608` s důvodem).
- argon2id s rehash, v DB jen SHA-256 otisk klíče relace, cookie `HttpOnly; Secure;
  SameSite=Lax`, stejně dlouhá odpověď pro neexistující účet (`backend/app/bezpecnost.py:26`),
  CSRF přes `Origin`, CSP/HSTS/X-Frame-Options (`backend/app/main.py`).
- Test `test_jen_cteni_zadny_zapis` projde celé OpenAPI a ověří 403 na každý zápis – odolné
  vůči novým endpointům. Pravidla letů pokryta velmi dobře včetně kontroly stejné chyby
  přímo v DB.

### Zjištění

- **K1 (kritické) Správce osob si vygeneruje odkaz pro heslo admina.**
  `POST /api/ucty/{osoba_id}/pozvanka` (`backend/app/prihlasovani.py:604-619`) je chráněn jen
  `Depends(spravuje_osoby)` a odkaz vrací v JSON. `ucet_zmenit` má pojistku „Účet admina smí
  měnit jen admin“ (`:582-584`), `osoba_zmenit` „Admina smí vypnout jen admin“
  (`backend/app/osoby.py:287-288`), pozvánka ne. Nastavení hesla (`:409-427`) ověřuje jen
  `smi_se_prihlasit`. Správce osob tak převezme účet admina. Doporučení: v `ucet_pozvanka`
  (a pro konzistenci i v e-mailové variantě) odmítnout cíl `admin = true`, pokud volající není
  admin; totéž pro změnu e-mailu admina v `osoba_zmenit`; test „správce osob nezíská odkaz
  pro admina“.
- **S1 (důležité) STARTTLS bez ověření certifikátu.** `backend/app/posta.py:36` volá
  `smtp.starttls()` bez `context` → neověřený kontext, heslo k `info@lkkl.cz` lze při MITM
  odchytit. Doporučení: `smtp.starttls(context=ssl.create_default_context())`.
- **S2 (důležité) Zablokování prozrazuje existenci účtu a jde zneužít.** Neznámý e-mail
  vrací vždy 401, existující po 5 pokusech 429 (`backend/app/prihlasovani.py:326-363`);
  počítadlo je jen per účet, takže kdokoli zvenčí zablokuje libovolného pilota. Doporučení:
  limit i podle IP a 429 i pro neznámé e-maily, nebo vědomě přijmout a zapsat do návrhu.
- **S3 (důležité) Tři implementace „UPDATE jen poslaných sloupců“** (`lety.py:877-881`,
  `osoby.py:290-296`, `vycvik.py:218-230`) a dvě verze překladu chyb DB → HTTP. Doporučení:
  jedna pomocná funkce v `db.py` a jedna mapa výjimek psycopg na HTTP stavy s hláškami.
- **S4 (drobné) Pool a souběh.** `max_size=5` (`backend/app/db.py:17-26`), endpointy
  synchronní; odeslání e-mailu (timeout 10 s) drží spojení z poolu po celou dobu SMTP.
  Doporučení: `max_size` ~10, kratší timeout se srozumitelnou 503, e-mail až po uvolnění
  spojení.
- **S5 (drobné)** `assert _pool is not None` v aplikačním kódu (`db.py:70`) – pod `-O` zmizí.
  502 vrací surový text SMTP chyby (`prihlasovani.py:676-677`). Prošlé relace nikdo
  automaticky neuklízí (`prikazy uklid` bez cronu). Mimo `lkkl.posta` žádný logger –
  neočekávané chyby DB končí jako generická 500 bez `diag`.
- **S6 (drobné) Chybějící testy:** K1; 429 vs 401 u neznámého účtu; „přihlásit jako“ +
  úprava letu → audit nese `puvodni_osoba_id`; `kontrola_puvodu` s více adresami; `lifespan`
  a parsování `DB_SOCKET` (`nastaveni.py:46-69`).

## 5. Frontend a design uživatelského prostředí

### Silné stránky

- **Normalizace stylů funguje.** Grep na hex/px/rem/ms mimo `styly/tokeny.css` nenašel nic;
  stylelint to vynucuje (`frontend/stylelint.config.js`), ESLint zakazuje `style=` v JSX.
  Varianty komponent jen přes vlastní proměnné (`--tl-*`, `--stitek-*`), výjimky mají
  komentář `VÝJIMKA:`.
- **Datová vrstva.** Jeden `api.ts` s hláškami pro 0/502–504/4xx, globální 401 → odhlášení,
  hierarchické klíče TanStack Query s cílenou invalidací, `zmenitUzivatele` zahazuje cizí
  data při přepnutí účtu.
- **Čas:** vše UTC (`cas.ts`), „teď“ podle serveru, přechod půlnoci refetchem, výběr času
  mřížkou bez klávesnice.
- **Přístupnost nad průměr:** `aria-pressed`, `role="checkbox"`, `role="status"/"alert"`,
  Esc pro nabídku i panel, `N`/`Ctrl+Z` na desce; e2e selektory sémantické (`getByRole`),
  bez `waitForTimeout`.
- TS `strict` + `noUncheckedIndexedAccess` + `verbatimModuleSyntax`; každý soubor začíná
  odkazem na návrh.

### Design UX

**Mobil (375 px, palec, slunce) – velmi dobrý.** Hlavní akce dole: „Nový let“ v přilepené
liště, PŘISTÁL/VZLET v posledním řádku pásku (PŘISTÁL širší), oznámení se ZPĚT nad nimi.
Pásky jako stripy ŘLP: rejstřík a stopky 20 px tučně, barva jen výplní + text varování –
stav je rozpoznatelný i při slabém kontrastu na slunci. Průvodce 3 kroky s rozpracovaným
páskem nahoře. Slabiny: 12px šedý text (funkce, typ, štítky, drobný text deníku) je na slunci
nejhůř čitelný prvek – zvážit 12 px jen pro nadpisy a štítky; prázdná obrazovka při načítání
(F2); malé dotykové cíle sekcí (F8).

**Desktop (1366/1920 px, myš, dispečer) – odpovídá maketě v7 a `docs/modul-desktop.md`.**
Lišta, řada letadel s proužkem stavu a oranžovou polohou, sloupec pásků ≤ 760 px, deník
jeden řádek na let, souhrny z `v_souhrn_dne`, časová osa jako SVG s pásmy soumraku, panely
zprava přes deník při ovladatelných páscích (ověřeno testem `deska.spec.ts:60-93`). Hustota
správná: na 1920 px celý den bez posouvání. Dobré detaily: `--dotyk` přemapované na 32/40 px
uvnitř `.deska`, prstenec vybraného pásku i na ose. Slabiny: pásky a řádky editoru nejsou
fokusovatelné (F7); dialog je mobilní bottom sheet 480 px i na 1920 px. Je to skutečně jiná
obrazovka pro jiného uživatele, ne responzivní varianta.

### Zjištění

- **F1 (důležité) Požadavek bez časového limitu.** `frontend/src/api.ts:17` volá `fetch` bez
  `AbortSignal`. Na slabém signálu zůstane PŘISTÁL zašedlé desítky sekund. Doporučení:
  `signal: AbortSignal.timeout(15_000)` a převod `TimeoutError` na `ChybaApi(0, …)`.
- **F2 (důležité) Prázdná obrazovka při načítání.** `frontend/src/App.tsx:92`
  (`if (!error) return null`) a `stranky/Lety.tsx:52-62` při prvním načtení nerendrují nic.
  Doporučení: hlavička + „Načítám…“.
- **F3 (důležité) Chybná hláška offline na desce.** `frontend/src/deska/Deska.tsx:100-104`
  ukáže „údaje z 00:00:00 UTC“, i když se lety nikdy nenačetly (`dataUpdatedAt === 0`); mobil
  to řeší správně. Doporučení: podmínka `letyDne.error && letyDne.data`.
- **F4 (důležité) Duplicita pásku mobil × deska.** `lety/Pasek.tsx:127-148` a
  `deska/PasekDeska.tsx:18-52` jsou dvě `CasLetu`; totéž markup „typ · vlečná“ a CSS
  `.let-stopky`/`.pasek-stopky`, `.let-varovani`/`.pasek-varovani`. Doporučení: společné
  přihrádky (`Rejstrik`, `CasLetu`, `Varovani`) + jedna třída; mobil a deska skládají jen
  mřížku.
- **F5 (důležité) Žádné jednotkové testy.** Čistá logika (`cas.ts`, `poradi.ts`,
  `Volby.tsx rychlaVolba`, `CasovaOsa.tsx pasma`, `novyLet.tsx ucelyPro/hotovo`) se testuje
  jen přes Playwright nad DB. Doporučení: `vitest` do `npm run kontrola`; `useNovyLet`
  rozdělit na čistou funkci `odvodit(novy, nabidky)` + tenký hook (dnes vrací 30 položek,
  `novyLet.tsx:216-246`).
- **F6 (důležité) E2e jen v Chromiu** (`playwright.config.ts`: Pixel 7); iPhone je výslovný
  cíl. Testy `akce.spec.ts:73,112` závisejí na pořadí v souboru. Doporučení: druhý projekt
  WebKit pro `lety`, `akce`, `prihlaseni`; stav připravit v testu.
- **F7 (důležité) Pásky nejsou dostupné z klávesnice.** `lety/Pasek.tsx:167,313`,
  `deska/PasekDeska.tsx:87`, `vycvik/Editor.tsx:359-362,409-413,755-759` jsou `<div onClick>`
  bez `role`/`tabIndex`; `CasovaOsa.tsx:153` má `role="button"` bez `tabIndex`. Doporučení:
  `<button>` nebo `role="button" tabIndex=0` + Enter/Space.
- **F8 (důležité) Dotykový cíl pod 44 px bez výjimky.** `komponenty/Sekce.css:2-12`: výška
  jen řádku 12px písma, okraj v `margin`, ne `padding`; podobně `vycvik/Vycvik.css:99-120`.
  Doporučení: `min-height: var(--dotyk)` a odsazení do `padding`, nebo `VÝJIMKA:`.
- **F9 (drobné)** `tik.ts` zakládá `setInterval` na každé volání – na desce ~15
  nesynchronizovaných intervalů, stopky sousedních pásků tikají s různou fází. Doporučení:
  jeden sdílený store s jedním intervalem.
- **F10 (drobné) Velké soubory:** `vycvik/Editor.tsx` (938 ř., 14 komponent) →
  `Osnovy.tsx`, `Typy.tsx`, `prvky.tsx`, `Nahled.tsx`; `lety/novyLet.tsx` (772) →
  `novyLet.ts` + bloky; `lety/Detail.tsx` (544) → `AkceDetailu.tsx`, `Upravy.tsx`.
- **F11 (drobné)** Chybí prettier (vidět na `stranky/Lety.tsx:77-113`). `ch` není
  v `unit-disallowed-list` – `lety/Volby.css:16,38`, `deska/Deska.css:45` jsou pevné rozměry
  mimo tokeny. Vazba lety ↔ letadla přes text `rejstrik` místo id (`deska/RadaLetadel.tsx:54`,
  `Souhrny.tsx:65`, `CasovaOsa.tsx:78`). Čtyři kopie `useMutation + oznamit`
  (`provoz/api.ts`, `osoby/api.ts`, `sprava/api.ts`, `vycvik/api.ts`) → `useMutaceApi`.
- **F12 (drobné)** Zastaralé komentáře (`deska/PanelDetailu.tsx:11-12`, `deska/Lista.tsx:13`).
  Dialog bez správy fokusu a bez Esc. Blikání tmavého režimu (režim se nastaví až po načtení
  bundle, `main.tsx:18`) – inline skript v `<head>`. `theme-color #1c4587` neodpovídá tokenu
  akční modré. Manifest `standalone` bez service workeru – offline nejde. Jeden chunk
  415 kB (124 kB gzip) bez `lazy()` pro `vycvik/`, `osoby/`, `sprava/`.

## 6. Struktura a čitelnost kódu

- **Konzistence pojmenování je vzorná:** doménové názvy česky bez diakritiky, technické
  anglicky, stejné názvy přes DB → Python → TS (`cas_vzletu`, `spravuje_osoby`). Mrtvý kód
  v aplikaci nenalezen; mrtvé objekty jen v historii SQL skriptů (D4).
- **Komentáře říkají proč,** s datem rozhodnutí a odkazem na návrh – to je největší
  přednost pro čtenáře za rok.
- **Dluh je ve třech podobách:** (1) velké soubory – `lety.py` 907, `Editor.tsx` 938,
  `novyLet.tsx` 772, `prihlasovani.py` 739, `Detail.tsx` 544; (2) duplicity – práva (A1),
  UPDATE a překlad chyb (S3), pásek (F4), mutace s oznámením (F11); (3) ručně udržované
  zrcadlení typů (A2). Žádný z nich není urgentní, ale všechny porostou s každým modulem.
- **Formátování:** Python má ruff format, frontend nemá formátovač – přidat prettier.

## 7. Co dál (navrhované pořadí)

| # | Akce | Rozsah |
|---|---|---|
| 1 | K1: pojistka admina v pozvánce a změně e-mailu + test | 1 h |
| 2 | S1: `starttls(context=ssl.create_default_context())` | 10 min |
| 3 | F1 + F2 + F3: timeout `fetch`, stav „Načítám…“, podmínka offline hlášky | 1–2 h |
| 4 | D2: rozhodnout o `_data` (udržovat + CI, nebo jeden generovaný soubor) | 2 h |
| 5 | D1: role `lkkllog_app` bez vlastnictví schématu (skript 045 + nasazení) | 2–3 h |
| 6 | D4: `docs/schema.sql` z `pg_dump` v CI | 1 h |
| 7 | A2: generované typy API, `response_model` u `detail` a `nabidky` | 2 h |
| 8 | F5 + A4: vitest a pyright do kontrol | 2 h |
| 9 | A1, S3, F4, F10, A3: refaktoring duplicit a velkých souborů – po modulech, ne najednou | průběžně |

Body 1–3 doporučuji před dalším nasazením. Body 4–8 jsou investice do bezpečného růstu;
bod 9 se vyplatí dělat vždy při dalším zásahu do daného souboru, ne jako samostatný úkol.

## 8. Zpracování (9. 10. 2026)

Každý bod samostatným commitem (`git log ef6d2d4..`); kontroly a testy zelené (111 pytest,
`npm run kontrola` včetně 6 jednotkových testů, 43 klikacích), skript 045 vyzkoušen na kopii
serverové databáze.

**Hotovo:** K1 (pojistka admina + test), S1, S4, S5 (úklid relací aplikací při startu a při
přihlášení – cron není potřeba; pool 10; bez `assert`), F1, F2, F3, F5 (vitest v kontrole),
F7 (pomůcka `jakoTlacitko`, pásky a úsečky jako odkazy, řádky editoru jako tlačítka, viditelný
fokus), F8 (sekce 44 px, výjimky v editoru zdůvodněné), F9, F11 (`ch` jen v tokenech), F12
(dialog Esc + fokus, tmavý režim bez bliknutí, `theme-color` z tokenu, komentář lišty),
D2 (zastaralé `_data` 001/003 smazány; pravidlo: každý `_data` načítá e2e příprava), D4
(`docs/schema.sql` z `bash db/schema.sh`, CI hlídá shodu), D5, D6, D9 (skript 045), D8
(zmizelý skript = chyba, `pg_advisory_lock`, kontrola PostgreSQL ≥ 17; tabulka `lkkl.migrace`
zůstává výjimkou zapsanou v CLAUDE.md 12), D10.

**Rozhodnuto a zapsáno do návrhu (bez změny kódu):** S2 (`docs/modul-prihlasovani.md` 4.1),
D1 (`docs/nasazeni.md` – aplikace zůstává vlastníkem schématu, důvody), D3
(`docs/modul-lety.md` 3.2 – souběh vědomě přijat).

**Odloženo (podle bodu 9 výše – při dalším zásahu do souboru, ne samostatně):** A1, A2
(generované typy API, `response_model` u `detail`/`nabidky`), A3, S3, F4, F10. **Neprovedeno
s důvodem:** A4 – pyright nad `app/` hlásí 217 chyb, téměř vše typování řádků psycopg
(`Connection[DictRow]`, `LiteralString` u skládaných dotazů); vyplatí se až spolu s S3
(jedna pomocná funkce pro UPDATE). F6 – WebKit v CI potřebuje systémové balíčky (pomalé
zrcadlo Ubuntu, viz komentář v `ci.yml`); iPhone se zkouší ručně. F12 zbytek (`lazy()`
chunky, service worker, dialog jako bottom sheet na 1920 px) a D7 (indexy) – při tisících
letů ročně nepostřehnutelné. S5 – 502 nese text chyby SMTP dál (vidí ho jen admin, je i
v `lkkl.email.chyba`). S6 – doplněn test ke K1 a k úklidu relací; ostatní navržené testy ne.

**Doplněno 10. 10. 2026 (po nasazení v2.24.0):** S3 (`db.transakce` s jedním překladem chyb
databáze – podle názvu omezení, druhu chyby nebo výchozí; `db.upravit` pro UPDATE poslaných
sloupců), A1 (práva jen v modelu `Prava`, závislost `pravo(název)`), A2 (`response_model` všude,
modely dědí z `app/model.py`, typy frontendu generované z OpenAPI do `src/api.gen.ts` –
`npm run api-typy` v kontrole, CI hlídá shodu; ručně opsané typy pryč, tsc prošel beze změny
obrazovek) a S6 (testy: neznámý účet 401 i po pokusech, víc adres původu, audit při „přihlásit
jako“, `DB_SOCKET`). Z review tak zbývá jen bod 9 (A3, F4, F10 při dalším zásahu do souborů)
a vědomě neprovedené A4, F6, F12 zbytek, D7.
