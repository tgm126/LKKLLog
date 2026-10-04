# Licence, medical a rozlétanost – podklady

Shrnutí předpisů, ze kterých vychází hlídání licencí, medicalu a rozlétanosti v LKKL Log.
Je to podklad pro manuál a nápovědu. Za rozlétanost odpovídá pilot a v detailech platí
předpis v aktuálním znění, případně výklad ÚCL nebo LAA ČR. Stav k říjnu 2026.

## Letouny – EASA Part-FCL (PPL(A), LAPL(A), třída SEP a TMG)

| Co | Podmínka | Předpis |
|---|---|---|
| Let s cestujícími (PPL i LAPL) | za posledních **90 dní** aspoň **3 vzlety, přiblížení a přistání** jako jediný pilot u řízení na stejném typu nebo ve stejné třídě. Let se 2× T&G = 3 vzlety a přistání. V noci aspoň jedno v noci. | FCL.060(b) |
| LAPL(A) – průběžná rozlétanost | za posledních **24 měsíců** jako pilot letounu nebo TMG: **12 h jako PIC** včetně **12 vzletů a 12 přistání** a **aspoň 1 h letu s instruktorem**. Kdo nesplní: přezkoušení s examinátorem, nebo dolétat chybějící pod dohledem instruktora. | FCL.140.A |
| PPL(A) – kvalifikace SEP / TMG | platí **24 měsíců** od data v průkazu. Prodloužení zkušeností: v **12 měsících před koncem platnosti** **12 h**, z toho **6 h jako PIC**, **12 vzletů a 12 přistání**, **1 h s instruktorem** (FI nebo CRI). Jinak přezkoušení. | FCL.740.A(b) |

## Kluzáky – EASA Part-SFCL (SPL; LAPL(S) se převádí na SPL)

| Co | Podmínka | Předpis |
|---|---|---|
| Kluzáky (bez TMG) | za posledních **24 měsíců** na kluzácích **5 h** jako PIC nebo dvojmo či sólo pod dohledem FI(S), včetně **15 startů** a **2 cvičných letů s FI(S)**. Nebo přezkoušení s FE(S). | SFCL.160(a) |
| Způsob vzletu | každý způsob zvlášť: za posledních **24 měsíců** aspoň **5 startů**, u startu gumou (bungee) **2**. Naviják zahrnuje i start za automobilem. | SFCL.130, SFCL.160 |
| TMG pod SPL | za posledních **24 měsíců** **12 h** jako PIC nebo dvojmo či pod dohledem, z toho na TMG **6 h**, **12 vzletů a 12 přistání** a **cvičný let aspoň 1 h s instruktorem**. Neplatí pro toho, kdo má TMG v licenci podle Part-FCL (PPL/LAPL). | SFCL.160(b), (c) |
| Cestující | za posledních **90 dní** jako PIC aspoň **3 starty** na kluzáku. Pro TMG **3 vzlety a přistání** na TMG, v noci aspoň jedno v noci. | SFCL.160(e) |

Dvouletá lhůta u cvičných letů se podle AMC počítá od posledního dne měsíce, ve kterém let
proběhl.

## Ultralehké letouny – LAA ČR (průkaz pilota ULL)

| Co | Podmínka | Zdroj |
|---|---|---|
| Platnost průkazu | **2 roky**. Prodloužení na žádost s prohlášením o náletu **aspoň 5 h za poslední 2 roky**. | Aeroweb, LAA ČR |
| Propadlý průkaz | propadlý déle než **90 dní** (nebo bez doloženého náletu): prodloužení až po letu s inspektorem LAA ČR. | LAA ČR |
| Cestující | obdobu „3 vzlety za 90 dní“ jsme ve veřejných zdrojích nenašli. **Ověřit u LAA ČR.** | – |

## Radiofonní průkaz – ČTÚ

| Co | Podmínka | Zdroj |
|---|---|---|
| Průkaz radiotelefonisty letecké pohyblivé služby, omezený (OFL) nebo všeobecný (VFL) | platí **10 let** od vydání, pak se prodlužuje **o 5 let** | vyhláška č. 157/2005 Sb. |
| Prodloužení | písemná žádost na ČTÚ **aspoň měsíc před koncem platnosti**, poplatek, doklad o praxi. Po propadnutí lze do 1 roku požádat o nový průkaz. | vyhláška č. 157/2005 Sb. |

## Jazyková způsobilost – EASA FCL.055

| Úroveň | Platnost |
|---|---|
| 4 (operační) | 4 roky od přezkoušení |
| 5 (rozšířená) | 6 let |
| 6 (expertní) | trvale |

Piloti, kteří používají radiotelefonii, potřebují jazykovou způsobilost v angličtině nebo
v jazyce, který se ke spojení používá (v ČR i čeština). Aplikace při zakládání letu varuje,
jen když nemá platnou úroveň v žádném jazyce. Na blížící se konec platnosti upozorňuje
3 měsíce předem.

## Medical (Part-MED)

- Jedno osvědčení může mít **pro různé třídy různou platnost**, např. třída 2 a LAPL.
  Aplikace proto ukládá platnost ke každé třídě zvlášť.
- **PPL(A)** potřebuje třídu 1 nebo 2. **LAPL(A), SPL a ULL** stačí i medical LAPL.
  Rozhoduje nejdelší platnost vhodné třídy.
- Medical je citlivý údaj. Aplikace eviduje jen třídu a datum platnosti. Vidí je sám
  pilot, správce licencí a letadel a admin.

## Jak to počítá aplikace

- **Zdroj dat:** jen lety zapsané v LKKL Log. Lety jinde a lety před začátkem evidence
  (případně před importem z Flight Office) aplikace nezná.
- **Vzlety a přistání:** let = 1 vzlet a tolik přistání, kolik je `pocet_pristani`
  (1 + T&G). Každé T&G je zároveň vzlet.
- **Let s instruktorem:** let, na kterém byl pilot žák nebo přezkoušený.
- **„Platí do“:** datum, kdy podmínka přestane platit, pokud pilot už nepoletí. Počítá se
  tak, že se od nejnovějších letů sčítá, dokud není podmínka splněná. K datu letu, který ji
  doplnil, se přičte lhůta (90 dní nebo 24 měsíců).
- **Kategorie:** motorové = třída SEP, TMG = TMG, kluzák = kluzáky bez TMG, UL = ULL.
- **Hlídání** zapíná admin v *Nastavení provozu* po modulech: způsobilost pilotů (doklady),
  rozlétanost pilotů (nálet za období, cestující) a způsobilost letadel (termíny). Zapne je,
  až budou data kompletní. Varování nic neblokuje.

## Kdo co vydává

- **ÚCL (Úřad pro civilní letectví)** je český úřad pro průkazy podle předpisů EASA:
  PPL(A), LAPL(A), SPL, medical. Jeho postupy (CAA-ZLP-…) popisují vydání,
  prodlužování a obnovu kvalifikací v ČR.
- **LAA ČR** vydává průkazy pilotů ULL a technické průkazy ultralehkých letadel.

## Zdroje

### ÚCL (česky)
- CAA-ZLP-163 Způsobilost pilotů letounů: https://www.caa.cz/wp-content/uploads/2019/07/CAA-ZLP-163-Zpu%CC%8Asobilost-pilotu%CC%8A-letounu%CC%8A.pdf
- CAA-ZLP-165 Prodlužování a obnova kvalifikací pilotů letounů: https://www.caa.cz/wp-content/uploads/2022/11/CAA-ZLP-165-Prodluzovani-a-obnova-kvalifikaci-pilotu-letounu_rev-30.11..pdf
- Žádost o průkaz LAPL(A) podle Part-FCL (formulář ZLP-F-163-22): https://www.caa.cz/wp-content/uploads/2020/11/ZLP-F-163-22-0-Zadost-o-Part-FCL-LAPLA.pdf
- Seminář SPL (ÚCL, 17. 2. 2024): https://caa.cz/wp-content/uploads/2024/02/4-Prezentace-OZLP.pdf
- CAA-ZLP-049 Způsobilost pilotů kluzáků (starší národní úprava pro GPL, nahrazená SPL podle Part-SFCL; postup pro SPL je CAA-ZLP-161): https://www.caa.cz/wp-content/uploads/2019/07/049-GPL.pdf
- EASA GM k prodloužení rozlétanosti (na webu ÚCL): https://www.caa.gov.cz/wp-content/uploads/2020/05/EASA-GM_Recency_extension_rev.2.pdf

### EASA – jazyková způsobilost
- FCL.055 (Part-FCL, Easy Access Rules): https://easa.europa.eu/cs/downloads/116578/en

### ČTÚ (radiofonní průkaz)
- Vyhláška č. 157/2005 Sb. (druhy průkazů odborné způsobilosti a doba jejich platnosti): https://epravo.cz/top/zakony/sbirka-zakonu/vyhlaska-ze-dne-19-dubna-2005-o-nalezitostech-prihlasky-ke-zkousce-k-prokazani-odborne-zpusobilosti-k-obsluze-vysilacich-radiovych-zarizeni-o-rozsahu-znalosti-potrebnych-pro-jednotlive-druhy-odborne-zpusobilosti-o-zpusobu-provadeni-zkousek-o-druzich-prukazu-odborne-zpusobilosti-a-dobe-jejich-platnosti-14599.html
- ČTÚ – osnovy a otázky ke zkouškám (OFL): https://ctu.gov.cz/sites/default/files/obsah/osnovyofl_2019-07.pdf

### Letadla (pro budoucí rozšíření)
- UK CAA – Part-ML (údržba lehkých letadel, ARC): https://www.caa.co.uk/general-aviation/aircraft-ownership-and-maintenance/part-ml
- LAA ČR – technické průkazy SLZ: https://www.laacr.cz/sluzby-pilotum/technicke-prukazy/

### EASA a další

- EASA Part-FCL (Easy Access Rules): https://easa.europa.eu/cs/downloads/116578/en
- LAPL – přehled: https://en.wikipedia.org/wiki/Light_aircraft_pilot_licence
- UK CAA – LAPL(A): https://www.caa.co.uk/general-aviation/pilot-licences/aeroplanes/light-aircraft-pilot-licence-for-aeroplanes
- Prodloužení SEP/TMG (FCL.740.A): https://ffac.ch/wp-content/uploads/2020/09/SEP-TMG-revalidation-EASA.pdf
- Prodloužení SEP/TMG – formulář Luftfartstilsynet: https://www.luftfartstilsynet.no/globalassets/dokumenter/skjema/sertifikat-og-rettigheter/fixed-wingfly/nf-1092-revalidation-of-sep-land-sep-sea-and-or-tmg-ver.-6.0-03-2026.pdf
- EASA Easy Access Rules for Sailplanes – SFCL.160: https://www.owoba.de/fliegerei/easa/sfcl.160.pdf
- BGA – rolling recency: https://members.gliding.co.uk/rolling-recency/
- BGA – Guidance for SPL holders: https://members.gliding.co.uk/wp-content/uploads/sites/3/2020/10/Guidance-for-SPL-holders.pdf
- Aeroweb – pilot ULL: https://www.aeroweb.cz/pilotni-prukazy/ultralighty/pilot-ultralehkych-letounu-ull
- LAA ČR – pilotní průkazy: https://www.laacr.cz/sluzby-pilotum/pilotni-prukazy/
- LAA ČR – technické průkazy SLZ (platnost 2 roky, prototypy 1 rok): https://www.laacr.cz/sluzby-pilotum/technicke-prukazy/
- LAA ČR – předpisy a formuláře (UL 1, UL 2, UL 3): https://www.laacr.cz/ultralehke-letouny/ul-predpisy-a-formulare/
- LAA ČR – UL 1 Pravidla provozu SLZ (2026): https://www.laacr.cz/tml/files/2026/09/2026-09-02_UL-1.pdf
