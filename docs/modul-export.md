# Modul: export záznamů o letech (PDF e-mailem)

Zadání 10. 10. 2026, odsouhlaseno 10. 10. 2026 (rozhodnutí v kap. 9), realizace skriptem
`db/047_export.sql`.

Zadání: osoby, které lety archivují na papíře a přepisují do účetního programu, si nechají
poslat **denní** nebo **měsíční** přehled letů jako **PDF v příloze e-mailu**. Adresát je
zatím napevno admin. Navazuje na `modul-email.md` (odesílání, záznam e-mailů)
a `v_souhrn_dne` (db/036, 044).

## 1. Rozsah
- Dva druhy: **den** (jeden den) a **měsíc** (kalendářní měsíc). Den letu jako všude:
  UTC datum vzletu (`v_let.den`).
- Jen **ukončené lety** (zrušené a naplánované se nevypisují). Nedokončené lety období
  (ve vzduchu) se nevypíšou, ale PDF na ně **upozorní v záhlaví** („Pozor: 1 let není
  ukončený – OK-1234, vzlet 14:02“) – export se kvůli nim neblokuje (uzávěrky nejsou).
- Formát jen PDF (A4 na šířku). Jiné formáty (CSV, Excel, Flight Office) až s potřebou.
- Export **nic nezamyká** a neukládá snímek dat – oprava letu po odeslání se projeví
  v dalším exportu; co bylo odesláno, je v e-mailu.

## 2. Právo
Nový příznak účtu (pravidlo „práva = logické příznaky na účtu“):

```sql
ALTER TABLE lkkl.ucet ADD COLUMN smi_exportovat boolean NOT NULL DEFAULT false;
COMMENT ON COLUMN lkkl.ucet.smi_exportovat IS
    'Smí si nechat poslat export letů (PDF e-mailem); admin smí vždy.';
-- + popisek auditu ('ucet', 'smi_exportovat', 'exportuje lety'), sloupec ve v_ucet
```
- Přiděluje admin v detailu osoby (blok Účet a přihlášení, vedle ostatních práv).
- Server hlídá: příznak nebo admin; v relaci **jen ke čtení** ne (stejně jako ostatní akce).

## 3. Obsah PDF
**Záhlaví** (každá strana): AK Kladno – Záznam letů · den „čtvrtek 9. 10. 2026“ nebo
měsíc „říjen 2026“ · časy UTC · strana 1/3. **Patička:** vytvořeno 10. 10. 2026 13:20 UTC,
kdo (jméno), verze aplikace.

**Tabulka letů** (seřazeno podle vzletu; u měsíce po dnech s mezisoučtem dne):

| č. | Letadlo | Typ | PIC | Další posádka | Účel / úloha | Vzlet (způsob) | Odkud | Kam | Vzlet | Přistání | Doba | Přist. | POB | Hradí | Poznámka |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|

- Další posádka s funkcí („žák: Novák J.“, „dozor: …“, „přezkoušený: …“).
- Účel / úloha: „Výcvik IU/4“, „Přezkoušení PC-SEP“, vlečný let „Vlek → OK-1234“.
- Vzlet (způsob): naviják / vlastní / „aerovlek OK-ABC“. Kluzák a jeho vlečná jdou
  v tabulce **pod sebou** (stejný čas vzletu).
- Hradí: jméno plátce, nebo „aeroklub“. Soukromé letadlo je označené štítkem „soukromé“.
- Dodatečně zapsaný let je označený („dopsáno“).

**Souhrny** (za tabulkou):
1. **Podle letadel** – z `v_souhrn_dne`: lety, přistání, minuty (h:mm), navijáky; vlečná ve
   vleku zvlášť; plachtařský a motorový provoz zvlášť s mezisoučty.
2. **Podle plátců** – osoba / aeroklub: počet letů, minuty po letadlech (podklad
   pro účetnictví). Nový pohled `v_souhrn_platce` (den, plátce, letadlo, lety, minuty,
   přistání) – ze stejných pravidel jako `v_souhrn_dne`.

Na konci řádek pro podpis „Zkontroloval: … dne …“.

## 4. Odeslání
- E-mail z info@lkkl.cz (stávající `posta.py`, rozšířená o přílohu).
- **Adresát:** všichni admini, kteří se smějí přihlásit (kap. 9, bod 3), každý zvlášť.
- Předmět „AK Kladno Log – lety 9. 10. 2026“ / „– lety říjen 2026“, krátký text (kdo
  export vyžádal, počet letů, upozornění na neukončené), příloha
  `lety-2026-10-09.pdf` / `lety-2026-10.pdf`.
- Omezení: od jedné osoby nejvýš 1 export za minutu (dvojklik).

## 5. Záznam
Stávající tabulka `lkkl.email` (obsah ani PDF se neukládá – jde kdykoli vytvořit znovu):

```sql
ALTER TABLE lkkl.email DROP CONSTRAINT email_druh_check,
    ADD CONSTRAINT email_druh_check CHECK (druh IN ('ODKAZ_HESLO', 'EXPORT_LETU')),
    ADD COLUMN obdobi daterange,                         -- exportované dny [od, do)
    ADD CONSTRAINT email_obdobi CHECK ((druh = 'EXPORT_LETU') = (obdobi IS NOT NULL));
```
`osoba_id` = adresát (admin), `odeslal_id` = kdo export vyžádal.

## 6. Obrazovka
Položka nabídky **Export letů** (jen s právem). Mobil celá obrazovka, desktop sloupec
uprostřed (jako Správa).
- Přepínač **Den | Měsíc**.
- Den: **kalendář po měsících** ze Smazat lety dne (tučné dny s počtem letů, ostatní šedé)
  – komponenta se přesune do společných a použije v obou obrazovkách.
- Měsíc: seznam posledních 12 měsíců s počtem letů (prázdné šedé).
- Po výběru: „Poslat PDF – čtvrtek 9. 10. 2026, 23 letů – na admin@…“ → **Poslat** →
  oznámení „Odesláno na …“ nebo chyba.

## 7. Rozhraní
| Volání | Co dělá |
|---|---|
| `GET /api/export` | dny s ukončenými lety a počtem a adresy, kam export přijde (s právem exportu) |
| `POST /api/export` `{druh: "DEN" \| "MESIC", den}` | sestaví PDF, pošle, zapíše do `email`; vrátí adresu a počet letů |

Modul `backend/app/export.py` (dotazy a rozhraní) + `export_pdf.py` (sazba).

## 8. Technika
- Knihovna **fpdf2** (čistý Python, tabulky s opakovaným záhlavím, žádné systémové
  knihovny v Dockeru; LGPL). Alternativy: ReportLab (větší), WeasyPrint (HTML → PDF, ale
  potřebuje Pango v image).
- Písmo s češtinou vložené do PDF: **DejaVu Sans** (volná licence) jako soubor v
  `backend/app/pisma/`.
- Testy: server (právo, jen ke čtení, období, jen ukončené lety, vlek pod sebou, souhrny,
  upozornění na neukončené, příloha v e-mailu, záznam, omezení 1/min) – text PDF se čte
  knihovnou `pypdf` (jen vývojová závislost). Klikací (mobil): položka jen s právem,
  kalendář, odeslání, oznámení.
- Příručka: situace „Potřebuji lety na papír / do účetnictví“.

## 9. Rozhodnutí (10. 10. 2026)
1. **Papírový vzor** není – sloupce podle kap. 3.
2. **Soukromá letadla** se vypisují se štítkem „soukromé“ (aerovlek soukromého kluzáku se
   platí); v souhrnu podle letadel také označená. (V1 je z účetního exportu vynechávala.)
3. **„Napevno admin“** = všechny účty s právem admin, které se smějí přihlásit (adresy
   z databáze, nic se nenastavuje); každý admin dostane vlastní e-mail a vlastní řádek
   v `email`. Později nejspíš „poslat mně“.
4. **Stažení v prohlížeči** zatím ne.
5. **Časy UTC** (jako celá aplikace).
6. **Řádek pro podpis** na konci PDF ano.
7. **Měsíc** i běžící (průběžná kontrola).
