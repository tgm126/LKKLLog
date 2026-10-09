# Modul: osnovy a úlohy (NÁVRH k odsouhlasení)

Zadání 9. 10. 2026: editace osnov výcviku a jejich úloh v aplikaci – **jen desktop**, se
**zvláštním právem**. Důležité jsou vazby úlohy na **kategorii letadla** a **účel letu**,
musí být vidět **hierarchie** a to, **kde se úloha nabízí v novém letu** (zaškrtávátka).
Maketa: `docs/navrhy/osnovy-desktop.html` (skutečná data ze serveru 9. 10. 2026).

## 1. Dnešní stav a problém
- `lov_osnova (kod, nazev, poradi, platny, kategorie_id)` → `lov_uloha (…, osnova_id)` →
  vazba `lov_uloha_ucel (uloha_id, ucel_id)`; nabídka pohledem `v_uloha_nabidka`.
- **Kategorie je u osnovy, ne u úlohy.** Všechny 4 osnovy jsou „Kluzák“, ale osnova II má
  úlohy pro TMG (II/10–12) – dnes se nabízejí jen u letu kluzáku, u TMG ne.
- Úpravy jen přímo v databázi.

## 2. Datový model (změny)
```sql
-- kategorie u úlohy (M:N), místo jedné kategorie osnovy
CREATE TABLE lkkl.lov_uloha_kategorie (
    uloha_id     bigint NOT NULL REFERENCES lkkl.lov_uloha,
    kategorie_id bigint NOT NULL REFERENCES lkkl.lov_kategorie,
    PRIMARY KEY (uloha_id, kategorie_id)
);
-- převod: každá úloha dostane kategorii své osnovy (osnova bez kategorie = všechny platné)
ALTER TABLE lkkl.lov_osnova DROP COLUMN kategorie_id;
-- zvláštní právo na účtu
ALTER TABLE lkkl.ucet ADD COLUMN spravuje_osnovy boolean NOT NULL DEFAULT false;
```
- **Nabídka** `v_uloha_nabidka`: úloha × účel × kategorie, jen platná úloha i osnova (jako
  dnes); z ní průvodce i kontrola letu (`let_zkontrolovat`: úloha musí patřit k účelu
  a kategorii letadla; povinnost úlohy jen tam, kde nějaká existuje – beze změny pravidla).
- Vazba `lov_uloha_kategorie` hlídaná platností (`kontrola_platnosti`, db/031).
- **Audit** na `lov_osnova`, `lov_uloha`, `lov_uloha_ucel`, `lov_uloha_kategorie` (úpravy
  z aplikace i z databáze) s čitelnými popisky.
- Po převodu opravit II/10–12 na TMG – v editoru (nebo rovnou v migraci, rozhodnete).

## 3. Obrazovka (desktop)
Nabídka uživatele → Správa → **Osnovy a úlohy** (admin, nebo právo *spravuje osnovy*) →
**panel přes celou desku**. Na telefonu položka není.
- **Matice** vlevo – hierarchie osnova → úlohy:
  - řádek **osnovy** (sbalitelný): název, počet úloh, „+ úloha“; souhrnná zaškrtávátka
    (plné / prázdné / částečně) – klik nastaví všem úlohám osnovy; platná;
  - řádky **úloh**: pořadí ▲▼, název (např. „IU/4 Navijákové vzlety…“), zaškrtávátka
    **účel** (Normální · Výcvik · Sólo · Přezkoušení; u povinných „povinná“) a **kategorie**
    (Kluzák · Letoun · TMG · UL), počet letů s úlohou, platná;
  - úloha bez účelu nebo bez kategorie: oranžově „nenabízí se“.
- Vpravo **vybraná úloha** (název, přesun do jiné osnovy, smazat) a **náhled nového letu**:
  volba účelu a kategorie → osnovy a úlohy přesně jak je uvidí pilot v bloku Úloha
  (povinná / nepovinná, nebo že se blok neukáže).
- Každá změna se uloží hned a zapíše do historie; dole Nová osnova · Nová úloha · Zavřít.

## 4. Pravidla
- **Kód** (`kod`) vytvoří server – nikde se nezobrazuje (standard číselníku).
- **Smazat** jde jen úlohu bez letů (s vazbami) a osnovu bez úloh; použitou úlohu nebo osnovu
  jen **zneplatnit** – ve starých letech zůstane, nikde se nenabízí.
- Přesun úlohy do jiné osnovy jde (lety odkazují na úlohu, ne na osnovu).
- Pořadí ▲▼ v osnově (`poradi`), osnovy mezi sebou stejně.
- Právo *spravuje osnovy* přiděluje admin v detailu osoby (jako ostatní práva); server hlídá.

## 5. Testy
Server: práva (403), převod kategorií (II/10–12), nabídka podle účelu a kategorie, kontrola
letu s novou vazbou, smazání jen nepoužitého, audit. Klikací (desktop): matice, souhrnné
zaškrtnutí osnovy, náhled, pořadí, nová úloha, zneplatnění.

## 6. K rozhodnutí
1. **Kategorie u úlohy** (vazba M:N) místo u osnovy – souhlas? (doporučuji; jinak TMG úlohy
   v osnově II nejdou.)
2. **Právo *spravuje osnovy*** – samostatné (doporučuji, např. vedoucí výcviku), nebo jen admin?
3. **Povinnost úlohy u účelu** (`lov_ucel.uloha_povinna` – dnes výcvik, sólo, přezkoušení):
   v editoru jen zobrazit (doporučuji), nebo i měnit?
4. II/10–12 přepnout na TMG už v migraci, nebo ručně v editoru?
