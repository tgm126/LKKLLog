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
- **Hlídání** (varování při zakládání letu a přehled rozlétanosti) zapíná admin v *Nastavení
  provozu*, až budou licence a medical zadané u všech pilotů. Varování nic neblokuje.

## Zdroje

- EASA Part-FCL (Easy Access Rules): https://easa.europa.eu/cs/downloads/116578/en
- ÚCL – EASA GM k prodloužení rozlétanosti: https://www.caa.gov.cz/wp-content/uploads/2020/05/EASA-GM_Recency_extension_rev.2.pdf
- LAPL – přehled: https://en.wikipedia.org/wiki/Light_aircraft_pilot_licence
- UK CAA – LAPL(A): https://www.caa.co.uk/general-aviation/pilot-licences/aeroplanes/light-aircraft-pilot-licence-for-aeroplanes
- Prodloužení SEP/TMG (FCL.740.A): https://ffac.ch/wp-content/uploads/2020/09/SEP-TMG-revalidation-EASA.pdf
- Prodloužení SEP/TMG – formulář Luftfartstilsynet: https://www.luftfartstilsynet.no/globalassets/dokumenter/skjema/sertifikat-og-rettigheter/fixed-wingfly/nf-1092-revalidation-of-sep-land-sep-sea-and-or-tmg-ver.-6.0-03-2026.pdf
- EASA Easy Access Rules for Sailplanes – SFCL.160: https://www.owoba.de/fliegerei/easa/sfcl.160.pdf
- BGA – rolling recency: https://members.gliding.co.uk/rolling-recency/
- BGA – Guidance for SPL holders: https://members.gliding.co.uk/wp-content/uploads/sites/3/2020/10/Guidance-for-SPL-holders.pdf
- Aeroweb – pilot ULL: https://www.aeroweb.cz/pilotni-prukazy/ultralighty/pilot-ultralehkych-letounu-ull
- LAA ČR – pilotní průkazy: https://www.laacr.cz/sluzby-pilotum/pilotni-prukazy/
- LAA ČR – předpisy a formuláře (UL 1, UL 2, UL 3): https://www.laacr.cz/ultralehke-letouny/ul-predpisy-a-formulare/
- LAA ČR – UL 1 Pravidla provozu SLZ (2026): https://www.laacr.cz/tml/files/2026/09/2026-09-02_UL-1.pdf
