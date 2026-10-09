# LKKL Log – příručka pro uživatele

Elektronický sešit letů aeroklubu Kladno. Zapisuje se **kdo, na čem, kdy a odkud kam letěl**;
doby, počty a souhrny dne aplikace spočítá sama. Data dál přebírá účetní.

Příručka je podle situací, ne podle tlačítek – aplikace vede sama a chybějící údaj ukáže
(„vyberte“, „Chybí: …“).

---

## Pro všechny

**Přihlášení.** E-mail a heslo. Účet a odkaz pro nastavení hesla dává správce osob (aplikace
e-maily neposílá – odkaz vám předá). Přihlášení platí 30 dní od posledního použití.

**Telefon, nebo počítač.** Na telefonu (a v úzkém okně) je přehled letů pod sebou a nový let
jako průvodce po krocích. Na počítači (okno od 1200 px) je **provozní deska** – vše na jedné
obrazovce, ovládání myší. Data jsou stejná, přepínat nic netřeba.

**Čas je vždy UTC** (jako v letectví). Nahoře je čas UTC a sluneční časy letiště:
TB / TE = začátek a konec občanského soumraku, SR / SS = východ a západ Slunce.

**Pás letu = strip.** Zelený letí, modrý je naplánovaný, červený má problém (varování:
po konci soumraku, přes maximální dobu letu). Štítky říkají jen odchylky od běžného letu
(výcvik, naviják / aerovlek, POB, úloha); trasa odkud → kam.

**Každá akce jde vrátit.** Po VZLET, PŘISTÁL a T&G se na 6 s ukáže ZPĚT (na počítači i
Ctrl+Z). Omyl zjištěný později opravíte v detailu letu (ťuknutí na pásek).

**Let se nemaže, ruší se s důvodem** (technická závada, počasí, založeno omylem, přerušený
vzlet, jiné). Zrušený let jde obnovit. Každá změna je v historii letu (kdo a kdy).

**Nabídka uživatele** (kolečko s iniciálami vpravo nahoře):
- **Můj provoz · dnes** – jen pro vás, na tomto zařízení a jen na dnešek:
  - **Letiště** – kde dnes létáte (jinak domovské Kladno). Podle něj sluneční časy
    a výchozí místo přistání.
  - **Osoby v provozu** – kdo je dnes na letišti; rychlá volba posádky pak nabízí jen je
    (ostatní najde Hledat…).
- **Režim zobrazení** – podle zařízení / světlý / tmavý.
- **Odhlásit.**

**Žlutý pruh TESTOVACÍ PROVOZ** = zkušební provoz; zapsané lety se mohou smazat.

---

## Přišel jsem si zalítat a jsem sám
1. **Nový let** → letadlo → v posádce **Já** (PIC). Účel normální, POB 1 a místa jsou
   předvyplněné. Místo vzletu je tam, kde letadlo **naposledy přistálo**.
2. **VZLET TEĎ** – čas vzletu se zapíše v okamžiku stisku.
3. Po přistání **PŘISTÁL** na pásku. Okruhy s dotykem (motorová letadla, TMG, UL) –
   **T&G** při každém dotyku; přistání celkem se spočítá samo.
4. Letíte jinam? Před vzletem nastavte **místo přistání** (v Dalších údajích); trasa
   je pak vidět na pásku.

**Zapomněl jsem zapsat.** Nový let → **Proběhlý let** → vyberte čas vzletu a přistání
(nesmí být v budoucnosti). Let se označí „dodatečně“.

**Let kratší než minuta** (přerušený vzlet): aplikace se při PŘISTÁL zeptá – počítat jako let
(1 minuta), nebo zrušit jako přerušený vzlet.

---

## Létáme, je nás víc
- **Naplánujte si pořadí:** Nový let → … → **Naplánovat**. Naplánované lety čekají v přehledu
  (modře) a VZLET stiskne kdokoli, kdo je u toho – jednou; druhý stisk už nic nezapíše
  a ukáže, kdo a kdy to udělal.
- **Posádka podle účelu:**
  - normální let – PIC (POB zadáte, kolik je na palubě);
  - **výcvik** – instruktor (PIC) a žák; **sólo** – žák a dozor na zemi;
    **přezkoušení** – examinátor (PIC) a přezkoušený. U výcviku vyberte **úlohu** z osnovy.
  - Rychlá volba nabízí jen ty, kdo roli smí podle oprávnění (a jsou v provozu, máte-li je
    vybrané); kohokoli jiného najde **Hledat…**.
- **Kdo platí:** předvyplní se podle účelu (normální → PIC, výcvik a sólo → žák,
  přezkoušení → přezkoušený), nebo **aeroklub**. Jde změnit u letu.
- Jeden člověk ani letadlo nemohou být ve vzduchu ve dvou letech zároveň – aplikace to
  nedovolí.

---

## Jsem na věži / u stolu s počítačem (provozní deska)
- **Nahoře řada letadel**: kdo letí (běžící čas), co je naplánované, dnešní nálet; oranžový
  kód letiště = letadlo naposledy přistálo jinde než na vašem letišti. Klik na letadlo na zemi
  = nový let s ním; na letící nebo naplánované = jeho detail.
- **Pásky** (ve vzduchu, naplánované): PŘISTÁL, T&G, VZLET přímo na pásku; klik na pásek
  otevře **detail v panelu** – deska zůstává ovladatelná.
- **Klávesy:** **N** = nový let, **Esc** = zavřít panel, **Ctrl+Z** = Zpět poslední akce.
- **Deník dne** – ukončené lety (řádek na let), pod nimi zrušené; patička: lety, přistání,
  doba.
- **Souhrny** – plachtařský provoz (kluzáky a vleky) a motorový provoz (i TMG) po letadlech;
  na notebooku za tlačítkem Souhrny.
- **Časová osa dne** – úsečka za každý let, pásma soumraku a noci; klik = detail.
- **Jiný den** – šipky u data (‹ ›): deník, souhrny a osa toho dne.
- Červený pásek = hlídejte: let **po konci občanského soumraku** nebo **přes maximální dobu**
  letadla.

---

## Jsem v plachtařském provozu
- **Naviják:** kluzák → posádka → způsob vzletu **Naviják** → VZLET TEĎ (nebo Naplánovat).
  Aplikace si pamatuje, jak se dnes naposledy startovalo.
- **Aerovlek:** kluzák → posádka → **Aerovlek** → vyberte **vlečnou a vlekaře** (předvyplní se
  poslední vlekař té vlečné). Vznikne **dvojitý pásek** – kluzák a vlečná:
  - **vzlétají společně** (jeden VZLET pro oba), **přistávají zvlášť** – PŘISTÁL u každé
    poloviny;
  - naplánovaný vlek se ruší celý; po vzletu je každý let samostatný (přetržené lano: kluzák
    zrušte jako přerušený vzlet, vlečná letí dál);
  - vlekař nemůže být v posádce kluzáku.
- **Cizí vlečná** (nás vleče jiný klub): musí být založená mezi letadly (soukromá, vlečná)
  a její pilot mezi osobami – požádejte správce; poprvé pilota najdete přes Hledat…, příště
  se nabídne sám.
- **Výcvik:** instruktor a žák, úloha z osnovy (u výcviku povinná); sólo s dozorem na zemi.
- T&G kluzák ani vlečná nemají.

---

## Jsem v klubovně na sdíleném počítači
Přihlaste se se zaškrtnutým **Jen ke čtení**: vidíte vše (deska, deník, souhrny), ale nic
nejde změnit – ani omylem cizí rukou. Pro zápis se odhlaste a přihlaste znovu normálně.

---

## Opravuji let
Ťuknutí na pásek nebo řádek deníku → **detail**. Údaje se opravují na místě (ťuknutí na
pole): posádka, POB, úloha, časy, místa, počet přistání, plátce, poznámka. U vleku se čas
vzletu opraví kluzáku i vlečné najednou. Změnil-li let mezitím někdo jiný, aplikace ukáže
aktuální stav a opravu zopakujete. Dole **Zrušit let** (s důvodem) / **Obnovit let**;
**Historie** ukáže všechny změny.

---

## Jsem správce
- **Osoby** (na telefonu, záložka Osoby – jen s právem): údaje, člen klubu, **aktivní**
  (neaktivní se nenabízí a nepřihlásí), oprávnění pro kategorie letadel; účet: **Smí se
  přihlásit**, práva, odblokování, **Odkaz pro heslo** (zkopírujte a předejte osobě).
- **Letadla** (na telefonu): přepínač **mimo provoz** (dočasně – vidět šedě, nejde vybrat).
  Vyřazené letadlo (prodané) a nová letadla zatím jen přímo v databázi.
- **Správa** v nabídce uživatele (jen admin): **Smazat lety dne…** – kalendář, dny s lety
  tučně, potvrzení (nevratné, v historii zůstane záznam) – a **Nastavení** (testovací provoz =
  žlutý pruh).
- Číselníky (účely, způsoby vzletu, letiště, osnovy…) se upravují přímo v databázi;
  nepoužívaná položka se nemaže, ale zneplatní (`platny = false`) – pak se nikde nenabízí.
