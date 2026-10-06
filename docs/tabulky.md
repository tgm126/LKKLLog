# Tabulky nové verze (schéma `lkkl`)

**Číselníky (`lov_*`)** mají jednotný standard: `id`, `kod` (jedinečný, jen pro program),
`nazev` (text pro zobrazení, nemusí být jedinečný), `poradi`, `platny`. Pravidla sloupců jsou
v doménách `lkkl.kod`, `lkkl.nazev`, `lkkl.poradi`, `lkkl.platny` (skript 008).
Každý číselník má **pohled pro nabídky** `v_lov_<název>`: jen platné položky, seřazené podle
pořadí a názvu (skript 010). Vazby a stará data pracují s tabulkami, zneplatněná položka u nich zůstane.

Průběžný seznam. Definice jsou v SQL skriptech `db/`; tabulky první verze viz
`tabulky-v1.md`.

| Objekt | Druh | Účel | Skript |
|---|---|---|---|
| `lov_kategorie` | číselník | kategorie letadel | 001, 008 |
| `lov_typ` | číselník | typy letadel → kategorie, počet míst | 001, 002, 008 |
| `letadlo` | tabulka | letadla: rejstříková značka, typ, soukromé, max. doba letu, vlečné | 001, 002 |
| `v_letadlo` | pohled | letadla s názvem typu, kategorií a počtem míst | 001, 002 |
| `lov_letiste` | číselník | česká letiště; kódem je ICAO; domovské (nejvýš jedno), souřadnice, nadmořská výška [ft] | 003, 008 |
| `lov_ucel` | číselník | účel letu: NORMALNI, VYCVIK, VYCVIK_SOLO, PREZKOUSENI (vlek se odvodí z vazby) | 008 |
| `lov_zpusob_vzletu` | číselník | VLASTNI, NAVIJAK, VLEK | 008 |
| `lov_funkce` | číselník | funkce jmenovitě uvedené osoby: PIC, ZAK, PREZKOUSENY, DOZOR; `na_palube` (počítá se do POB) | 008 |
| `lov_duvod_zruseni` | číselník | důvod zrušení letu | 008 |
| `ucel_funkce` | pravidlo | povinné funkce účelu kromě PIC (výcvik → žák, sólo → dozor, přezkoušení → přezkoušený) | 009 |
| `let` | tabulka | let: letadlo, účel (prázdný = vlečný let), způsob vzletu, vazba na vlečný let, místa (letiště nebo popis; nezadané = domovské), časy UTC, doba (počítá DB), doba 0 u krátkého letu, počet přistání, POB, plátce nebo aeroklub, poznámka, zrušení, založení, verze | 009 |
| `posadka` | tabulka | jmenovitě uvedené osoby letu s funkcí; osoba i funkce nejvýš jednou na letu | 009 |
| `let_tg` | tabulka | časy jednotlivých T&G (nepovinné) | 009 |
| `v_let` | pohled | lety s odvozeným stavem, dnem, vlekem, účtovanou dobou, POB (u účelů s funkcemi z posádky), PIC, plátcem a příznakem „dodatečně“ | 009, 011 |
| `let_kontrola` (+ `posadka_kontrola`, `let_tg_kontrola`) | trigger na konci transakce | jeden PIC, funkce podle účelu, POB, vlek, časy T&G | 009 |
| `let_doplnit_misto` | trigger | nezadané místo vzletu / přistání = domovské letiště | 009 |
| `let_verze`, `let_nemazat` | trigger | verze záznamu se zvyšuje; let nejde smazat | 009 |
| `osoba` | tabulka | osoby: jméno, příjmení, e-mail (jedinečný bez ohledu na velikost písmen), telefon (+420…), číslo člena (text, jen u členů), člen / externí, aktivní | 004 |
| `ucet` | tabulka | přihlašovací účet osoby (1:0..1, existence = aktivace v aplikaci): otisk hesla, aktivní, práva `admin` a `smi_odblokovat`, pozvánka, ochrana proti hádání hesla | 005, 006 |
| `relace` | tabulka | přihlášená zařízení: otisk klíče z cookie, platnost 30 dní od poslední aktivity, „přihlásit se jako“ (`puvodni_osoba_id`) | 005 |
| `v_ucet` | pohled | účty s údaji osoby a příznakem „smí se přihlásit“ (bez otisku hesla) | 005, 006 |
| `ucet_osoba_ma_email` | trigger | účet jen pro osobu s e-mailem (neexistující osobu odmítne cizí klíč) | 005, 007 |
| `osoba_email_u_uctu` | trigger | osobě s účtem nejde smazat e-mail | 005 |
| `audit` | tabulka | auditní log: kdy, transakce, tabulka, klíč řádku, operace, změny (JSON „z → na“), zdroj (aplikace / databáze), kdo, skutečný admin, `let_id` (generovaný) | 012 |
| `audit` (na let, posadka, let_tg, osoba, ucet, letadlo) | trigger | zápis do auditu jednou obecnou funkcí; vynechané sloupce: `let.verze`, `ucet.heslo_hash`, `posledni_prihlaseni`, `neuspesne_pokusy` | 012 |
| `audit_jen_doplnovat`, `audit_bez_vyprazdneni` | trigger | audit nejde upravit, smazat ani vyprázdnit | 012 |
| `audit_popisek` | pravidlo | popisky sloupců pro čitelnou historii; sloupec bez popisku se neukazuje | 012 |
| `v_audit` | pohled | audit čitelně: kdo (i „jako“, „přímo v databázi“), akce odvozená ze změny, popis | 012 |
| `v_historie_letu` | pohled | historie letu: jedna akce (let + posádka + T&G v jedné transakci) = jeden řádek | 012 |

## Rozhodnutí pro další tabulky

- **Let:** stav se neukládá – odvodí se (připravený = bez vzletu, ve vzduchu = vzlet bez
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

**Záloha** lokálních dat: `bash db/zaloha.sh` → `C:\GIT\LKKLLog-zalohy` (mimo git; obnova
je popsaná v hlavičce skriptu).
