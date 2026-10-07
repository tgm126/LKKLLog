# Instruktoři a examinátoři – typy oprávnění (analýza 7. 10. 2026)

Podklad pro evidenci oprávnění osob v aplikaci. Jen přehled pravidel a doporučení pro datový
model – nic se zatím neimplementuje. Body označené **[ověřit]** nejsou potvrzené z úředního
textu (zdroj byl nepřímý nebo starší) – před zavedením do číselníku ověřit u ÚCL / LAA ČR.

Navazuje na `licence-a-rozletanost.md` (rozlétanost pilotů) a na myšlenky z první verze
(`navrh-v1.md` kap. 3.1 a 4.12: doklady osoby určují nabídky posádky, let nikdy nezablokují).

## 1. Kde co platí (podle druhu letadla v aeroklubu)

| Letadla | Předpis | Instruktor | Examinátor |
|---|---|---|---|
| Kluzáky (SPL), TMG pod SPL | EASA **Part-SFCL** (nařízení (EU) 2018/1976) | **FI(S)** | **FE(S)** |
| Letouny, TMG (LAPL(A), PPL(A)), vlečné | EASA **Part-FCL** (nařízení (EU) 1178/2011) | **FI(A)**, **CRI(A)** | **FE(A)** (u třídních kvalifikací i **CRE**) |
| Ultralehké letouny (ULL) | národní – **LAA ČR** (UL 1, UL 3, LA 1) | **instruktor ULL** | **inspektor provozu ULL** (závěrečné zkoušky) |

TMG (motorový kluzák) jde vyučovat dvojí cestou: FI(S) s rozšířením na TMG (pro SPL
s oprávněním TMG), nebo FI(A) / CRI(A) (pro LAPL(A) / PPL(A) s kvalifikací TMG).

## 2. Kluzáky – Part-SFCL

### FI(S) – instruktor kluzáků
- **Oprávnění** (SFCL.315): výcvik k SPL a k rozšířením SPL – další kategorie kluzáků,
  **způsoby vzletu** (navijákem, aerovlekem, samostartem; instruktor musí mít v daném způsobu
  praxi), **TMG**, **akrobacie** (základní / pokročilá), **lety v oblacích**, vlekání
  transparentů; s dalším rozšířením i výcvik nových instruktorů (**Flight Instructor
  Coach**). Instruktor vyučuje jen to, co sám smí létat.
- **Předpoklady** (SFCL.320): věk aspoň 18 let, 100 h jako PIC a 200 startů na kluzácích,
  instruktorský kurz, ověření způsobilosti (assessment of competence).
- **Omezený FI(S)** (SFCL.350): na začátku vyučuje **jen pod dohledem** neomezeného FI(S)
  určeného výcvikovou organizací (ATO / DTO / klub) a **nesmí povolit první sólo** ani
  první samostatný přelet. Omezení se odstraní po **15 h nebo 50 startech** výcviku
  (z toho 5 h / 15 startů může být na TMG).
- **Platnost:** osvědčení FI(S) **nemá datum konce platnosti** – místo toho platí požadavky
  na průběžnou praxi (SFCL.360): **za poslední 3 roky** instruktorské osvěžovací školení
  **a** 30 h nebo 60 startů (u TMG vzletů a přistání) výcviku jako FI(S); **za posledních
  9 let** výcvikový let pod dohledem FI(S) s oprávněním Flight Instructor Coach. Kdo nesplní,
  smí znovu vyučovat až po osvěžení a ověření způsobilosti.

### FE(S) – examinátor kluzáků
- **Oprávnění** (SFCL.415) podle praxe:
  - zkoušky a přezkoušení **SPL** – 300 h na kluzácích, z toho 150 h nebo 300 startů výcviku;
  - zkoušky pro rozšíření SPL na **TMG** – 300 h, z toho 50 h výcviku na TMG;
  - ověření způsobilosti pro vydání **FI(S)** – 500 h a standardizační kurz.
- **Platnost** (SFCL.460): **5 let**; prodloužení = examinátorské osvěžovací školení
  a v posledních 24 měsících předvedení zkoušky inspektorovi úřadu (nebo pověřenému
  examinátorovi).
- Examinátor obecně nesmí zkoušet žáka, kterého sám vycvičil ve větším rozsahu
  (střet zájmů) **[ověřit přesné znění SFCL.405]**.

### BI(S) – základní instruktor kluzáků (jen Spojené království)
- Od 15. 9. 2025 ve **Spojeném království** (UK CAA, změna jejich převzatého Part-SFCL):
  věk 16 let, 50 h jako PIC, smí vyučovat jen základní cvičení (seznamovací lety, nouzové
  postupy, první zkušenosti) **vždy pod dohledem** neomezeného FI(S).
- **V EU (a tedy v ČR) BI(S) zavedený není** – evropská pravidla pro kluzáky (EGU, EASA) ho
  neuvádějí **[ověřit, zda EASA nechystá obdobu]**. Do číselníku zatím nezařazovat.

## 3. Letouny a TMG – Part-FCL

### FI(A) – instruktor letounů
- **Oprávnění** (FCL.905.FI): výcvik k **LAPL(A)** a **PPL(A)**, k třídním kvalifikacím
  pro jednopilotní letouny (**SEP**, **TMG**), k **noci**, **vlekání** (kluzáků
  i transparentů) a **akrobacii**, za dalších podmínek výcvik instruktorů.
- **Omezený FI(A)** (FCL.910.FI): vyučuje pod dohledem, **nesmí povolit první sólo** ani
  první samostatný navigační let; omezení odpadne po **100 h výcviku** na letounech/TMG
  a dohledu nad **25 samostatnými lety** žáků.
- **Platnost:** **3 roky**. Prodloužení (FCL.940.FI): **dvě ze tří** – 50 h výcviku,
  instruktorské osvěžovací školení, ověření způsobilosti; **u každého druhého** prodloužení
  vždy ověření způsobilosti.

### CRI(A) – instruktor třídní kvalifikace
- **Oprávnění** (FCL.905.CRI): výcvik k vydání, prodloužení a obnovení třídní kvalifikace
  (pro aeroklub **SEP** a **TMG**), vlekání a akrobacie – jen na třídě, ve které skládal
  ověření způsobilosti. **Ne** výcvik k licenci LAPL/PPL od začátku.
- **Platnost:** **3 roky** (FCL.940.CRI) **[ověřit podmínky prodloužení]**.

### FE(A) – examinátor letounů (a CRE)
- **Oprávnění** (FCL.1005.FE) podle praxe:
  - zkoušky a přezkoušení **LAPL(A)** – 500 h na letounech/TMG, z toho 100 h výcviku;
  - zkoušky **PPL(A)** a přezkoušení třídních kvalifikací – 1000 h, z toho 250 h výcviku;
  - (CPL – 2000 h; pro aeroklub nepodstatné).
- **CRE** (examinátor třídní kvalifikace) smí přezkoušení SEP / TMG pro prodloužení.
- **Platnost:** **3 roky** (FCL.1025) **[ověřit]**; prodloužení přes standardizační
  osvěžení a předvedení zkoušky inspektorovi úřadu.

## 4. Ultralehké letouny – LAA ČR

Podle výcvikové osnovy **UL 3** (znění z 4. 12. 2008 **[ověřit, zda je stále platné]**)
a organizačního předpisu **LA 1**:
- **Instruktor ULL** – předpoklady: věk 21 let, 200 h na ULL, z toho 75 h jako velitel na
  dvoumístných ULL, praxe na aspoň 3 typech, 5 let nepřetržité pilotní praxe, teoretické
  přezkoušení, kontrolní let s hlavním inspektorem provozu, instruktorský kurz
  (41 letů / 6 h 20 min). Zkrácená cesta: držitel osvědčení instruktora letounů / TMG po
  přeškolení na typ; pilot letounů / TMG s 150 h (z toho 100 h na ULL) v kurzu.
- Instruktor povoluje žákovi **první samostatný let** a vede osobní list žáka; **závěrečnou
  zkoušku dělá inspektor provozu** (ne instruktor).
- **Inspektor provozu ULL** (LA 1, kap. 3.4 a 3.8) – jmenuje ho hlavní inspektor provozu;
  musí mít platný průkaz a **kvalifikaci instruktor** a 5 let praxe. Kontroluje instruktory,
  dělá závěrečné zkoušky a přiznává kvalifikace – v aeroklubu tedy role „examinátora“ ULL.
- Související kvalifikace (nejsou instruktorské): **vlekař ULL** (výcvik i přezkoušení dělá
  inspektor provozu s kvalifikací vlekař, kluzák pilotuje instruktor nebo examinátor
  kluzáků), **vysazovač**, **řízené lety VFR**, **zkušební pilot**.
- Platnost kvalifikace instruktora ULL v UL 3 není – **[ověřit v aktuálním UL 1 / u LAA]**
  (průkaz pilota ULL platí 2 roky).

## 5. Co z toho plyne pro aplikaci (k projednání)

1. **Číselník druhů oprávnění** (`lov_druh_opravneni`, standard číselníku): FI(S),
   FE(S), FI(A), CRI(A), FE(A), CRE, instruktor ULL, inspektor provozu ULL. U každého:
   předpis (SFCL / FCL / LAA), **které kategorie letadel pokrývá** (vazba na `lov_kategorie`),
   zda je **instruktorský** (smí vést výcvik) nebo **examinátorský** (smí přezkoušet),
   zda **má datum konce platnosti** (FI(A), CRI, FE: ano; FI(S): ne – jen průběžná praxe).
2. **Oprávnění osoby** (provozní tabulka, ne `lov_`?) – osoba, druh, **platnost do**
   (prázdné, kde se nevydává), příznak **omezený** (pod dohledem), **rozšíření**
   (číselník: TMG, naviják, aerovlek, samostart, akrobacie, oblaky, vlekání, noc,
   Flight Instructor Coach). K rozhodnutí: patří oprávnění osob mezi trvalá data (`lov_`)?
   Osoby jsou `lov_`, takže jejich oprávnění by logicky měla být také.
3. **Použití v letech** (jen nabídka a varování, let se nikdy nezablokuje):
   - výcvik → v poli „Instruktor (PIC)“ nejdřív osoby s instruktorským oprávněním pro
     kategorii letadla (a pro způsob vzletu, je-li evidován);
   - přezkoušení → v poli „Examinátor (PIC)“ examinátoři pro kategorii;
   - výcvik sólo → **dozor** jen neomezený instruktor (omezený nesmí povolit první sólo);
   - examinátor = instruktor téhož žáka → jen upozornění (střet zájmů).
4. **Průběžná praxe instruktora kluzáků** se dá spočítat z letů v aplikaci (lety s účelem
   výcvik, kde je osoba PIC: hodiny a starty za 3 roky) – stejně jako rozlétanost pilotů.
   Osvěžovací školení a dohled „coach“ jsou mimo lety → zadat ručně jako datum.
5. **Externí examinátor** (z jiného klubu) – osoba bez účtu, jen se jménem (jako v první
   verzi); oprávnění u něj stačí jako druh bez platnosti.

## Zdroje
- UK CAA Regulatory Library (převzaté znění Part-SFCL): [SFCL.315 FI(S) – oprávnění](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Regs/01030_SFCL.315.htm),
  [SFCL.350 omezená oprávnění](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Regs/01080_SFCL.350.htm),
  [SFCL.360 průběžná praxe](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Regs/01090_SFCL.360.htm),
  [SFCL.400 examinátoři](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Regs/01110_SFCL.400.htm),
  [SFCL.415 FE(S)](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Regs/01140_SFCL.415.htm),
  [SFCL.460 platnost FE(S)](https://regulatorylibrary.caa.co.uk/2018-1976/Content/Document%20Structure/03%20SFCL/2%20Regs/01190_SFCL.460.htm)
- Nařízení (EU) 2018/1976, příloha III (Part-SFCL): https://legislation.gov.uk/eur/2018/1976/annex/III/data.xht
- EASA Easy Access Rules for Aircrew (Part-FCL): [FCL.905.FI](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=30),
  [FCL.905.CRI](https://easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=32),
  [FCL.1005.FE](https://www.easa.europa.eu/en/document-library/easy-access-rules/online-publications/easy-access-rules-aircrew-regulation-eu-no?page=40)
- ÚCL – formulář prodloužení FI/IRI/CRI: https://www.caa.gov.cz/wp-content/uploads/2025/10/FI-IRI-CRI-Revalidation-Renewal-Form.pdf
- BGA (UK) – BI(S) a změny SFCL 2025: https://members.gliding.co.uk/bga-training-organisation/basic-instructor-sailplanes/,
  https://members.gliding.co.uk/2025/07/21/changes-to-sfcl/
- EGU – pravidla pro kluzáky v EU: https://glidingunion.eu/gliding-rules/
- LAA ČR – předpisy: https://www.laacr.cz/ultralehke-letouny/ul-predpisy-a-formulare/
  ([UL 3 výcviková osnova](https://www.laacr.cz/tml/files/2023/05/2012-04-UL3-ULL.pdf),
  [LA 1 organizační systém](https://www.laacr.cz/tml/files/2022/04/LA1_11.4.2022.pdf),
  [UL 1 pravidla provozu](https://www.laacr.cz/tml/files/2026/09/2026-09-02_UL-1.pdf))
