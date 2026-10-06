# Tabulky nové verze (schéma `lkkl`)

**Číselníky (`lov_*`)** mají jednotný standard: `id`, `kod` (jedinečný, jen pro program),
`nazev` (text pro zobrazení, nemusí být jedinečný), `poradi`, `platny`. Pravidla sloupců jsou
v doménách `lkkl.kod`, `lkkl.nazev`, `lkkl.poradi`, `lkkl.platny` (skript 008).

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
| `osoba` | tabulka | osoby: jméno, příjmení, e-mail (jedinečný bez ohledu na velikost písmen), telefon (+420…), číslo člena (text, jen u členů), člen / externí, aktivní | 004 |
| `ucet` | tabulka | přihlašovací účet osoby (1:0..1, existence = aktivace v aplikaci): otisk hesla, aktivní, práva `admin` a `smi_odblokovat`, pozvánka, ochrana proti hádání hesla | 005, 006 |
| `relace` | tabulka | přihlášená zařízení: otisk klíče z cookie, platnost 30 dní od poslední aktivity, „přihlásit se jako“ (`puvodni_osoba_id`) | 005 |
| `v_ucet` | pohled | účty s údaji osoby a příznakem „smí se přihlásit“ (bez otisku hesla) | 005, 006 |
| `ucet_osoba_ma_email` | trigger | účet jen pro osobu s e-mailem (neexistující osobu odmítne cizí klíč) | 005, 007 |
| `osoba_email_u_uctu` | trigger | osobě s účtem nejde smazat e-mail | 005 |

## Rozhodnutí pro další tabulky

- **Let:** stav se neukládá – odvodí se (připravený = bez vzletu, ve vzduchu = vzlet bez
  přistání, ukončený = obojí, zrušený = důvod zrušení). **POB** (počet osob na palubě) je
  jediný údaj o počtu lidí; pojem host se nezavádí – jménem jen funkce z `lov_funkce`
  (normální let: jen PIC). Počet přistání vždy, časy T&G volitelně v podtabulce. Vlek se
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
