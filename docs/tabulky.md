# Tabulky nové verze (schéma `lkkl`)

**Předpona `lov_` = trvalá data** (číselníky, osoby, letadla, osnovy, popisky auditu a vazby
mezi nimi); při zahájení ostrého provozu zůstávají (skript 017). Všechno ostatní kromě
technických tabulek `ucet`, `migrace`, `provoz` jsou **provozní data** –
pohled `v_provozni_tabulky`; test hlídá, že nová tabulka je vědomě zařazená.

**Jednoduché číselníky** mají jednotný standard: `id`, `kod` (jedinečný, jen pro program),
`nazev` (text pro zobrazení, nemusí být jedinečný), `poradi`, `platny`. Pravidla sloupců jsou
v doménách `lkkl.kod`, `lkkl.nazev`, `lkkl.poradi`, `lkkl.platny` (skript 008). Osoby, letadla
a vazby mají vlastní sloupce. **Pohled pro nabídky** `v_lov_<název>`: jen platné položky,
seřazené podle pořadí a názvu (skript 010). Vazby a stará data pracují s tabulkami,
zneplatněná položka u nich zůstane.

Průběžný seznam. Definice jsou v SQL skriptech `db/`; tabulky první verze viz
`tabulky-v1.md`.

| Objekt | Druh | Účel | Skript |
|---|---|---|---|
| `lov_kategorie` | číselník | kategorie letadel | 001, 008 |
| `lov_typ` | číselník | typy letadel → kategorie, počet míst | 001, 002, 008 |
| `lov_letadlo` | trvalá data | letadla: rejstříková značka, typ, soukromé, max. doba letu, vlečné, mimo provoz | 001, 002, 013, 017 |
| `v_lov_letadlo` | pohled | letadla s typem, kategorií a počtem míst; pořadí kategorie → typ → rejstřík; mimo provoz jsou vidět, ale nejdou vybrat | 017 |
| `lov_letiste` | číselník | česká letiště; kódem je ICAO; domovské (nejvýš jedno), souřadnice, nadmořská výška [ft] | 003, 008 |
| `lov_ucel` | číselník | účel letu: NORMALNI, VYCVIK, VYCVIK_SOLO, PREZKOUSENI (vlek se odvodí z vazby); `uloha_povinna` | 008, 016 |
| `lov_zpusob_vzletu` | číselník | VLASTNI, NAVIJAK, VLEK | 008 |
| `lov_funkce` | číselník | funkce jmenovitě uvedené osoby: PIC, ZAK, PREZKOUSENY, DOZOR; `na_palube` (počítá se do POB) | 008 |
| `lov_duvod_zruseni` | číselník | důvod zrušení letu | 008 |
| `lov_osnova` | číselník | osnova (skupina úloh) → kategorie letadla (prázdná = všechny); kluzáky: IU, IA, II podle Programu výcviku AeČR v.6 (úprava AK Kladno) | 016, 019 |
| `lov_uloha` | číselník | úloha (letové cvičení) → osnova; označení je součástí názvu („IU/4 Navijákové vzlety…“), pozemní přípravy se nezadávají | 016, 019 |
| `lov_uloha_ucel` | vazba | u kterých účelů se úloha nabízí (výcvik = dvojí, sólo, normální, přezkoušení) | 019 |
| `v_uloha_nabidka` | pohled | úlohy pro průvodce podle účelu a kategorie; úloha je povinná (výcvik, sólo, přezkoušení), jen když pro účel a kategorii nějaká existuje | 016, 019 |
| `lov_ucel_funkce` | vazba | povinné funkce účelu kromě PIC (výcvik → žák, sólo → dozor, přezkoušení → přezkoušený) | 009, 017 |
| `let` | tabulka | let: letadlo, účel (prázdný = vlečný let), způsob vzletu, vazba na vlečný let, místo vzletu i přistání vždy (letiště nebo popis; místo přistání do přistání = plán), časy UTC, doba (počítá DB, nejméně 1 minuta), počet přistání, POB, plátce nebo aeroklub, poznámka, zrušení, založení, verze | 009 |
| `posadka` | tabulka | jmenovitě uvedené osoby letu s funkcí; osoba i funkce nejvýš jednou na letu | 009 |
| `let_tg` | tabulka | časy jednotlivých T&G (nepovinné) | 009 |
| `v_let` | pohled | lety s odvozeným stavem (NAPLANOVAN, VE_VZDUCHU, UKONCEN, ZRUSEN), dnem, vlekem, účtovanou dobou, POB (u účelů s funkcemi z posádky), PIC, plátcem a příznakem „dodatečně“ | 009, 011, 014 |
| `let_kontrola` (+ `posadka_kontrola`, `let_tg_kontrola`) | trigger na konci transakce | jeden PIC, funkce podle účelu, POB, vlek, časy T&G, úloha (povinnost, účel, kategorie) | 009, 011, 016 |
| `let_osoby_bez_prekryvu()` | funkce (v `let_kontrola`) | osoba na palubě nemůže být ve vzduchu ve dvou letech zároveň (plánování volné, dozor na zemi se nepočítá); hláška s rejstříkem a časem druhého letu | 018, 025 |
| `let_letadlo_volne` | trigger (před zápisem letu) | letadlo nemůže mít dva překrývající se lety – hláška „OK-… už letí (vzlet 10:42 UTC, PIC …)“; omezení `letadlo_bez_prekryvu` zůstává jako pojistka pro souběh | 025 |
| `cas_hlasky()`, `let_popis_hlasky()` | funkce | čas v UTC a popis druhého letu (vzlet / doba, PIC) do chybových hlášek | 025 |
| `let_doplnit_misto` | trigger | nezadané místo vzletu i přistání = domovské letiště (aplikace posílá moje letiště) | 009, 027 |
| `let_verze`, `let_nemazat`, `let_nevyprazdnovat` | trigger | verze záznamu se zvyšuje; let nejde smazat ani vyprázdnit | 009, 017 |
| `lov_osoba` | trvalá data | osoby: jméno, příjmení, e-mail (jedinečný bez ohledu na velikost písmen), telefon (+420…), číslo člena (text, jen u členů), člen / externí, aktivní (příznak vlekař převeden do oprávnění) | 004, 015, 017, 021 |
| `lov_role` | číselník | role v letu, do které se nabízejí osoby podle oprávnění: INSTRUKTOR (výcvik · PIC), DOZOR (sólo · dozor), EXAMINATOR (přezkoušení · PIC), VLEKAR (vlečný let · PIC); kódy používá program | 024 |
| `lov_opravneni` | číselník | druh oprávnění osoby (FI(S), FE(S), FI(A), CRI(A), FE(A), CRE(A), instruktor a inspektor ULL, vlekař) | 021, 024 |
| `lov_opravneni_role` | vazba | k jakým rolím oprávnění opravňuje (instruktoři: instruktor, dozor; examinátoři: examinátor; vlekař: vlekař) | 022, 024 |
| `lov_opravneni_kategorie` | vazba | pro které kategorie letadel se oprávnění smí vydat (bez řádku = žádná) | 021, 024 |
| `lov_osoba_opravneni` | vazba | kdo má jaké oprávnění; `omezene` = instruktor pod dohledem (jen evidence); audit | 021, 024 |
| `lov_osoba_opravneni_kategorie` | vazba | pro které kategorie osoba oprávnění má; složené FK na oprávnění osoby a na povolené kategorie (`kategorie_povolena`); audit | 024 |
| `v_osoba_smi` | pohled | role, které osoba smí zastat (role, účel, funkce, kategorie letadla) – nabídky osob v průvodci a detailu | 024 |
| `v_osoba_opravneni` | pohled | přehled oprávnění osob s kategoriemi a omezením v jednom řádku (kontrola zadání) | 024 |
| `ucet` | tabulka | přihlašovací účet osoby (1:0..1, existence = aktivace v aplikaci): otisk hesla, aktivní, práva `admin`, `smi_odblokovat` a `spravuje_osoby` (admin má všechna automaticky), pozvánka, ochrana proti hádání hesla | 005, 006, 023 |
| `relace_provoz` | tabulka | můj provoz: nastavení relace na jeden den (UTC) – letiště (prázdné = domovské); jiný den se nebere v úvahu | 026 |
| `relace_provoz_osoba` | tabulka | osoby v provozu relace (filtr nabídky osob v posádce); žádný řádek = bez filtru | 026 |
| `v_relace_letiste`, `v_relace_osoba` | pohled | dnešní letiště relace (zvolené, jinak domovské) a dnešní osoby v provozu | 026 |
| `relace` | tabulka | přihlášená zařízení: otisk klíče z cookie, platnost 30 dní od poslední aktivity, „přihlásit se jako“ (`puvodni_osoba_id`) | 005 |
| `v_ucet` | pohled | účty s údaji osoby a příznakem „smí se přihlásit“ (bez otisku hesla) | 005, 006 |
| `ucet_osoba_ma_email` | trigger | účet jen pro osobu s e-mailem (neexistující osobu odmítne cizí klíč) | 005, 007 |
| `lov_osoba_email_u_uctu` | trigger | osobě s účtem nejde smazat e-mail | 005, 017 |
| `migrace` | tabulka | evidence provedených skriptů `db/` (skript, kdy, otisk); zakládá ji spouštěč `app/migrace.py` | – |
| `audit` | tabulka | auditní log: kdy, transakce, tabulka, klíč řádku, operace, změny (JSON „z → na“), zdroj (aplikace / databáze), kdo, skutečný admin, `let_id` (generovaný) | 012 |
| `audit` (na let, posadka, let_tg, lov_osoba, lov_osoba_opravneni, lov_osoba_opravneni_kategorie, ucet, lov_letadlo) | trigger | zápis do auditu jednou obecnou funkcí; vynechané sloupce: `let.verze`, `ucet.heslo_hash`, `posledni_prihlaseni`, `neuspesne_pokusy` | 012 |
| `audit_jen_doplnovat`, `audit_nevyprazdnovat` | trigger | audit nejde upravit, smazat ani vyprázdnit | 012, 017 |
| `lov_audit_popisek` | číselník | popisky sloupců pro čitelnou historii; sloupec bez popisku se neukazuje | 012, 017 |
| `v_audit` | pohled | audit čitelně: kdo (i „jako“, „přímo v databázi“), akce odvozená ze změny, popis | 012 |
| `v_historie_letu` | pohled | historie letu: jedna akce (let + posádka + T&G v jedné transakci) = jeden řádek | 012 |
| `provoz` | technická | fáze provozu (jediný řádek): `testovani` → `pilot` → `ostry`; řídí žlutý pruh v aplikaci | 017 |
| `v_provozni_tabulky` | pohled | tabulky, které zahájení ostrého provozu vyprázdní (vše mimo `lov_` a technické) | 017 |
| `zahajit_ostry_provoz()` | funkce | jednorázově vyprázdní provozní tabulky (čísla od 1) a nastaví fázi `ostry`; zpět nejde | 017 |

## Rozhodnutí pro další tabulky

- **Let:** stav se neukládá – odvodí se (naplánovaný = bez vzletu, ve vzduchu = vzlet bez
  přistání, ukončený = obojí, zrušený = důvod zrušení). **POB** (počet osob na palubě) je
  jediný údaj o počtu lidí; pojem host se nezavádí. Kdo má funkci (žák, dozor, přezkoušený),
  je uveden jménem; jinak jen PIC + POB. U výcviku, sóla a přezkoušení se POB nezadává –
  odvodí se z posádky (skript 011). Počet přistání vždy, časy T&G volitelně v podtabulce. Vlek se
  odvodí z vazby kluzák–vlečná, „soukromé“ z letadla. Jedna úloha na let. Poznámka k letu.

- **Přistání do terénu** není letiště: u letu cizí klíč na letiště, nebo popis místa (právě jedno).
- **Aktivace v aplikaci** = založení přihlašovacího účtu (tabulka `ucet`, 1:0..1 k osobě);
  osoby se aktivují postupně (fáze 2 testování: vybraní pilotní uživatelé).
- **Práva v aplikaci** nejsou role, ale **logické příznaky výjimečných práv na účtu**
  (tabulka `ucet`, ne `osoba`): práva má jen ten, kdo se přihlašuje. Pojmenované jako práva
  (`smi_uzavirat_den`, `smi_spravovat_osoby`…), výjimkou je `admin` = smí všechno. Co smí
  každý přihlášený, příznak nemá. Novou potřebu řeší nový příznak (stejně vyžaduje nový kód).
  Změny práv zachytí auditní log. Seznam práv až s tabulkou `ucet` a přihlašováním.
- Datum narození se neeviduje (sloupec jde kdykoli přidat).
- **Úlohy:** u výcviku a sóla z osnovy pro kategorii letadla, u přezkoušení typ přezkoušení,
  u normálního letu úlohy z osnov i obecné (let do prostoru, okruhy, navigační let…).
  **Úlohy jsou členěné do osnov** (hierarchie): např. u kluzáků základní výcvik, pokračovací
  výcvik a sportovní výcvik. Návrh: číselník osnov (→ kategorie letadla) a číselník úloh
  (→ osnova); obecné úlohy jako samostatná osnova. V průvodci volba osnova → úloha (nebo úlohy
  seskupené podle osnovy). Osnovy a úlohy dodá uživatel.
- **Průvodce novým letem** nezadává poznámku ani místo vzletu (jen v detailu, editovatelné
  později). Plánovaný čas vzletu se zatím neeviduje.
- **Vlekař** je zatím příznak u osoby (015); s doklady se rozhodne, zda ho odvodit z kvalifikace.

**Záloha** lokálních dat: `bash db/zaloha.sh` → `C:\GIT\LKKLLog-zalohy` (mimo git; obnova
je popsaná v hlavičce skriptu).
