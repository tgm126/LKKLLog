# Návrh: oprávnění osob pro nabídku posádky (čistý model)

> **Odsouhlaseno 7. 10. 2026** (větev `navrh-opravneni`), realizace skriptem `db/024_opravneni_rozsah.sql`. Vychází z podkladů
> `podklady/instruktori-a-examinatori.md`, `podklady/prezkouseni.md`, `podklady/tmg-a-sep.md`.
> Navrženo bez ohledu na dnešní tabulky (skripty 021–022); srovnání se stávajícím modelem
> až v dalším kroku.

## 1. Účel a hranice

**Jediná otázka, na kterou model odpovídá:** *koho nabídnout do role v letu* – instruktora
do výcviku, dozor k sólu, examinátora k přezkoušení, vlekaře do vlečného letu – podle
kategorie letadla.

- Nabídka je **jen návrh** (rychlá volba nahoře, hledáním jde vybrat kohokoli). Let se kvůli
  oprávnění nikdy nezablokuje.
- Pilot, žák a přezkoušený se nabízí ze **všech aktivních osob** – pilotní průkazy se zatím
  neevidují (viz kap. 7).

## 2. Jak rozplést „džungli“: tři vrstvy

| Vrstva | Otázka | Kdo ji mění | Tabulky |
|---|---|---|---|
| **Předpisy** | Jaká oprávnění existují, pro jaké kategorie letadel je lze vydat a k jakým rolím opravňují | správce (zřídka) | `lov_opravneni`, `lov_opravneni_kategorie`, `lov_opravneni_role` |
| **Aplikace** | Jaké role v letu existují a kde v letu sedí (účel + funkce) | program (struktura) | `lov_role` |
| **Osoby** | Kdo má jaké oprávnění, pro které kategorie, zda omezené | správce osob | `lov_osoba_opravneni`, `lov_osoba_opravneni_kategorie` |

Spojení všech vrstev dá pohled **`v_osoba_smi`** (osoba – role – kategorie), ze kterého
aplikace bere nabídky.

Klíčová rozhodnutí, která „džungli“ zjednoduší:

1. **Role v letu jsou jen čtyři** (instruktor, dozor, examinátor, vlekař). Všechna
   oprávnění z předpisů se převedou na ně – aplikace nemusí znát FI, CRI, FE, CRE ani LAA.
2. **Rozsah (kategorie letadla) se drží u osoby, ne v názvu oprávnění.** Právo pro TMG (a u
   CRI/CRE pro třídu) je v předpisech vždy samostatné rozšíření; „FI(S)“ je jedno oprávnění,
   osoba ho má pro kluzáky, nebo pro kluzáky i TMG. Žádné řádky FI_S_TMG, CRI_A_SEP…
3. **Omezení (instruktor pod dohledem) je vlastnost oprávnění osoby, ne zvláštní druh
   oprávnění.** Omezený FI(S) je pořád FI(S); omezení se po splnění podmínek jen odškrtne.
   Na nabídku nemá vliv: omezený instruktor smí vyučovat i dozorovat sóla, jen nesmí povolit
   **první** sólo a první samostatný přelet (SFCL.350, FCL.910.FI) – a které sólo je první,
   aplikace neví.
4. **Kde role v letu sedí, je zapsané jednou u role**, ne u každého oprávnění zvlášť:
   „instruktor = PIC ve výcviku“, „dozor = dozor u sóla“.
5. Kategorie letadla v aplikaci (KLUZAK, TMG, LETOUN, UL) slouží i jako „třída“ z předpisů –
   v klubu LETOUN = třída SEP (land), jiné třídy klub nemá.

## 3. Tabulky

### 3.1 `lov_role` – role v letu (struktura, kódy používá program)

| Sloupec | Typ | Omezení | Význam |
|---|---|---|---|
| `id` | bigint identity | PK | |
| `kod` | `lkkl.kod` | UNIQUE | INSTRUKTOR, DOZOR, EXAMINATOR, VLEKAR |
| `nazev`, `poradi`, `platny` | domény | | standard číselníku |
| `ucel_id` | bigint NULL | FK `lov_ucel` | účel letu; **prázdný = vlečný let** (stejně jako `let.ucel_id`) |
| `funkce_id` | bigint NOT NULL | FK `lov_funkce` | funkce v posádce |
| | | UNIQUE NULLS NOT DISTINCT (`ucel_id`, `funkce_id`) | jedno místo v letu = nejvýš jedna role |

| kod | nazev | účel | funkce |
|---|---|---|---|
| INSTRUKTOR | Instruktor | VYCVIK | PIC |
| DOZOR | Dozor | VYCVIK_SOLO | DOZOR |
| EXAMINATOR | Examinátor | PREZKOUSENI | PIC |
| VLEKAR | Vlekař | (vlečný let) | PIC |

### 3.2 `lov_opravneni` – druh oprávnění (číselník podle standardu)

`id`, `kod`, `nazev`, `poradi`, `platny` – nic dalšího. Předpis (SFCL / FCL / LAA) je
součástí názvu, aplikace ho nepotřebuje.

| kod | nazev |
|---|---|
| FI_S | FI(S) instruktor kluzáků |
| FE_S | FE(S) examinátor kluzáků |
| FI_A | FI(A) instruktor letounů |
| CRI_A | CRI(A) instruktor třídy |
| FE_A | FE(A) examinátor letounů |
| CRE_A | CRE(A) examinátor třídy |
| INSTRUKTOR_ULL | Instruktor ULL |
| INSPEKTOR_ULL | Inspektor provozu ULL |
| VLEKAR | Vlekař (kvalifikace vlekání) |

### 3.3 `lov_opravneni_kategorie` – pro které kategorie lze oprávnění vydat

| Sloupec | Omezení |
|---|---|
| `opravneni_id` | FK `lov_opravneni` |
| `kategorie_id` | FK `lov_kategorie` |
| | PK (`opravneni_id`, `kategorie_id`) |

FI_S, FE_S → KLUZAK, TMG · FI_A, CRI_A, FE_A, CRE_A → LETOUN, TMG · INSTRUKTOR_ULL,
INSPEKTOR_ULL → UL · VLEKAR → LETOUN, UL (TMG předpis umožňuje, ale klub s TMG nevleká –
řídký případ, do nabídky nepatří).

### 3.4 `lov_opravneni_role` – k jakým rolím oprávnění opravňuje

| Sloupec | Omezení |
|---|---|
| `opravneni_id` | FK `lov_opravneni` |
| `role_id` | FK `lov_role` |
| | PK (`opravneni_id`, `role_id`) |

| | INSTRUKTOR | DOZOR | EXAMINATOR | VLEKAR |
|---|---|---|---|---|
| FI(S), FI(A), CRI(A), instruktor ULL | ✓ | ✓ | | |
| FE(S), FE(A), CRE(A), inspektor ULL | | | ✓ | |
| Vlekař | | | | ✓ |

Examinátor bývá zároveň instruktor – výcvik a dozor má díky svému oprávnění instruktora,
ne díky examinátorskému.

### 3.5 `lov_osoba_opravneni` – kdo má jaké oprávnění

| Sloupec | Omezení | Význam |
|---|---|---|
| `osoba_id` | FK `lov_osoba` | |
| `opravneni_id` | FK `lov_opravneni` | |
| `omezene` | boolean NOT NULL DEFAULT false | instruktor s omezením (vyučuje pod dohledem) |
| | PK (`osoba_id`, `opravneni_id`) | |

Audit triggerem (jako ostatní `lov_osoba*`). `omezene` je zatím **jen evidence** (nabídku
neovlivní, viz kap. 2 bod 3); později z něj může být upozornění u prvního sóla. Má smysl jen
u instruktorů – u jiných oprávnění nic nemění, samostatné omezení v databázi proto nezavádím.

### 3.6 `lov_osoba_opravneni_kategorie` – pro které kategorie ho osoba má

| Sloupec | Omezení |
|---|---|
| `osoba_id`, `opravneni_id` | FK → `lov_osoba_opravneni` (`osoba_id`, `opravneni_id`) |
| `opravneni_id`, `kategorie_id` | FK → `lov_opravneni_kategorie` (`opravneni_id`, `kategorie_id`) |
| | PK (`osoba_id`, `opravneni_id`, `kategorie_id`) |

**Dva složené cizí klíče** hlídají obojí: kategorie patří k oprávnění, které osoba opravdu
má, a oprávnění se pro tu kategorii smí vydávat (nikdo nebude mít FI(S) pro UL).
Oprávnění bez kategorie nedá žádnou roli (v aplikaci se ukáže jako „bez rozsahu“).
Audit triggerem.

## 4. DDL (náčrt)

```sql
CREATE TABLE lkkl.lov_role (
    id            bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod           lkkl.kod NOT NULL UNIQUE,
    nazev         lkkl.nazev NOT NULL,
    poradi        lkkl.poradi NOT NULL,
    platny        lkkl.platny NOT NULL,
    ucel_id       bigint REFERENCES lkkl.lov_ucel,          -- prázdný = vlečný let
    funkce_id     bigint NOT NULL REFERENCES lkkl.lov_funkce,
    UNIQUE NULLS NOT DISTINCT (ucel_id, funkce_id)
);

CREATE TABLE lkkl.lov_opravneni (
    id     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod    lkkl.kod NOT NULL UNIQUE,
    nazev  lkkl.nazev NOT NULL,
    poradi lkkl.poradi NOT NULL,
    platny lkkl.platny NOT NULL
);

CREATE TABLE lkkl.lov_opravneni_kategorie (
    opravneni_id bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    kategorie_id bigint NOT NULL REFERENCES lkkl.lov_kategorie,
    PRIMARY KEY (opravneni_id, kategorie_id)
);

CREATE TABLE lkkl.lov_opravneni_role (
    opravneni_id bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    role_id      bigint NOT NULL REFERENCES lkkl.lov_role,
    PRIMARY KEY (opravneni_id, role_id)
);

CREATE TABLE lkkl.lov_osoba_opravneni (
    osoba_id     bigint NOT NULL REFERENCES lkkl.lov_osoba,
    opravneni_id bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    omezene      boolean NOT NULL DEFAULT false,
    PRIMARY KEY (osoba_id, opravneni_id)
);

CREATE TABLE lkkl.lov_osoba_opravneni_kategorie (
    osoba_id     bigint NOT NULL,
    opravneni_id bigint NOT NULL,
    kategorie_id bigint NOT NULL,
    PRIMARY KEY (osoba_id, opravneni_id, kategorie_id),
    FOREIGN KEY (osoba_id, opravneni_id)     REFERENCES lkkl.lov_osoba_opravneni,
    FOREIGN KEY (opravneni_id, kategorie_id) REFERENCES lkkl.lov_opravneni_kategorie
);
-- + indexy na cizí klíče, audit triggery na obě osobní tabulky, popisky auditu

CREATE VIEW lkkl.v_osoba_smi AS          -- nabídky osob
SELECT DISTINCT oo.osoba_id, r.kod AS role_kod, u.kod AS ucel_kod, f.kod AS funkce_kod,
       k.kod AS kategorie_kod
FROM lkkl.lov_osoba_opravneni oo
JOIN lkkl.lov_opravneni o                   ON o.id = oo.opravneni_id AND o.platny
JOIN lkkl.lov_osoba_opravneni_kategorie ok  ON (ok.osoba_id, ok.opravneni_id) = (oo.osoba_id, oo.opravneni_id)
JOIN lkkl.lov_kategorie k                   ON k.id = ok.kategorie_id
JOIN lkkl.lov_opravneni_role orl            ON orl.opravneni_id = oo.opravneni_id
JOIN lkkl.lov_role r                        ON r.id = orl.role_id AND r.platny
LEFT JOIN lkkl.lov_ucel u                   ON u.id = r.ucel_id
JOIN lkkl.lov_funkce f                      ON f.id = r.funkce_id;
```

Pohled `v_osoba_opravneni` (přehled pro kontrolu, jeden řádek na osobu a oprávnění
s výčtem kategorií a příznakem omezení) zůstává jako pomůcka pro ruční úpravy v databázi.

## 5. Příklady

| Osoba | Zadání | Nabídne se jako |
|---|---|---|
| Instruktor kluzáků bez TMG | FI(S): KLUZAK | instruktor a dozor na kluzácích |
| Instruktor kluzáků i TMG, zároveň examinátor | FI(S): KLUZAK, TMG; FE(S): KLUZAK | instruktor a dozor na kluzácích a TMG; examinátor na kluzácích |
| Čerstvý instruktor | FI(S) **omezený**: KLUZAK | instruktor a dozor na kluzácích (první sólo hlídá instruktor) |
| Letoun a TMG, PPL | FI(A): LETOUN, TMG; VLEKAR: LETOUN | instruktor a dozor na letounech a TMG; vlekař na letounech |
| Examinátor jen třídy | CRE(A): LETOUN | examinátor na letounech |
| Externí examinátor | osoba „externí“ + FE(S): KLUZAK | examinátor na kluzácích |

**Školka** (začátek sezóny) se do modelu vejde beze změny: let s instruktorem = Výcvik
s úlohou 4 / 6 → nabídka INSTRUKTOR; sólo = Výcvik sólo → nabídka DOZOR (u jednomístného
typu dozor na zemi).

## 6. Vědomá zjednodušení (model je nezachycuje)

| Co předpis rozlišuje | Proč to pro nabídku nevadí |
|---|---|
| Na TMG cvičí pilota SPL jen FI(S), pilota LAPL/PPL jen FI(A)/CRI(A) | nabídka TMG ukáže oba druhy instruktorů; pilot ví, k jakému patří |
| FE(A) s 500 h jen LAPL; CRE jen přezkoušení a kvalifikace třídy, ne zkouška k průkazu | účel přezkoušení je jeden; vybírá pilot |
| FI(S) cvičí jen způsoby vzletu, které sám smí | v klubu mají instruktoři naviják i aerovlek |
| Platnost (FI(A) 3 roky, FE 5 let, instruktor ULL 2 roky), průběžná praxe | nabídka se podle platnosti neřídí; patří k evidenci dokladů |
| Examinátor nesmí zkoušet vlastního žáka (víc než 25 % výcviku) | jen upozornění, nikdy blokace – až bude potřeba |
| FIE(A), FE(S) pro ověření instruktorů, Flight Instructor Coach | v aplikaci pro ně není role |

## 7. Kudy dál (rozšíření bez přestavby)

- **Doklady s platností:** sloupec `platnost_do` v `lov_osoba_opravneni` (u oprávnění, která
  ji mají) – nabídka může neplatné řadit dozadu.
- **Pilotní průkazy a rozlétanost:** samostatné tabulky (`lov_prukaz` – SPL, LAPL(A), PPL(A),
  pilot ULL; `lov_osoba_prukaz` s kategoriemi/třídami a platností). Teprve z nich půjde
  rozlišit SPL × PPL na TMG a hlídat cvičné lety (2 s FI(S) za 24 měsíců…). Oprávnění podle
  tohoto návrhu se nemění.
- **Další role** (např. navijákář, služba RADIO) = nový řádek `lov_role` (a nový kód
  v programu) + vazby k oprávnění.

## 8. Rozhodnuté otázky

1. **Omezený instruktor a dozor:** smí. Omezený FI vyučuje pod dohledem a nesmí povolit
   jen **první** sólo a první samostatný přelet (SFCL.350(b), FCL.910.FI(b)); omezený FI(A)
   dokonce musí pro odstranění omezení **dozorovat aspoň 25 sól** žáků (FCL.910.FI(c)).
   Role proto žádný příznak „jen neomezené“ nemá.
2. **Vlekař pro TMG:** ne (správce 7. 10. 2026) – řídký případ.
3. **Inspektor ULL:** podle LA 1 čl. 3.8.4 musí inspektor provozu mít platný pilotní průkaz
   **a kvalifikaci instruktor**. Osoba má tedy obě oprávnění (instruktor ULL → instruktor
   a dozor, inspektor ULL → examinátor); vazby se nezdvojují.

Zdroje: [SFCL.350](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Regs/01080_SFCL.350.htm),
[FCL.905.FI / FCL.910.FI](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=30),
[LA 1](https://www.laacr.cz/tml/files/2022/04/LA1_11.4.2022.pdf).
