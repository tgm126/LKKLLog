# Modul: moje lety (rozhodnuto a realizováno 9. 10. 2026)

Zadání 9. 10. 2026: na **mobilu** záložka **Moje lety** pro všechny přihlášené. Seznam letů
jednoho dne (den jde vybrat), ťuknutí otevře **detail letu** – stejný jako ze záložky Lety,
i s úpravami.

## 1. Co je „můj let“
Let, kde jsem **v posádce** v jakékoli funkci: PIC, pilot ve výcviku, přezkoušený, dozor (na
zemi) – i vlečný let, kde jsem vlekař. „Já“ = osoba přihlášení (při „přihlásit se jako“ ta,
za kterou admin jedná). **Ne** lety, které jen platím nebo jsem jen založil (zapisuje je
časoměřič za ostatní) – to by seznam zahltilo.

## 2. Obrazovka (telefon)
- Menu: **Lety · Moje lety** (· Osoby · Letadla podle práv); Moje lety vidí každý, i jen ke
  čtení (detail pak bez úprav, jako dnes).
- Nahoře **výběr dne**: „‹ Pátek 9. 10. 2026 · dnes ›“, ťuknutí na datum otevře kalendář
  telefonu; výchozí dnešek, do budoucnosti nejde.
- Seznam stejně jako v záložce Lety: ve vzduchu a naplánované jako **pásky** (s akcemi VZLET,
  T&G, PŘISTÁL – jen dnes), ukončené a zrušené jako **deník** (u Ukončených „celkem“).
  Ťuknutí na let = detail letu (zpět vede do Moje lety na stejný den).
- Den bez mých letů: „V tento den nemáte žádný let.“

## 3. Server
- `GET /api/lety?den=RRRR-MM-DD&moje=true` – stejné pásky a deník jako dnes, jen lety, kde je
  přihlášená osoba v posádce (filtr v SQL přes `posadka`; u vleku i druhý let dvojice, aby
  pásek vleku byl celý).
- `GET /api/lety/moje-dny` – dny, kdy mám nějaký let (pro šipky).
- Nic nového v databázi.

## 4. Rozhodnutí (9. 10. 2026)
1. **Můj let = jen posádka** (ne plátce ani kdo let založil).
2. **Šipky ‹ ›** po **dnech s mými lety** (`GET /api/lety/moje-dny`); dopředu nejdál dnešek.
   Libovolný den kalendářem.
3. **Vzhled jako v Lety** – stejná komponenta (`PrehledLetu` ve `stranky/Lety.tsx`); souhrn
   dne je „celkem“ v sekci Ukončené.

## 5. Realizace
- Server: `GET /api/lety?moje=true` (filtr `posadka`, u vleku i druhý let dvojice),
  `GET /api/lety/moje-dny`; test `backend/tests/test_moje_lety.py`.
- Frontend: `stranky/MojeLety.tsx` (den v adrese `?den=`), záložka v menu; detail letu se
  vrací tam, odkud přišel (`useZpet`); klikací test `e2e/moje-lety.spec.ts`.
