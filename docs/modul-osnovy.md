# Modul: osnovy a úlohy (NÁVRH – rozpracováno, čeká na upřesnění uživatele)

Zadání 9. 10. 2026: editace osnov výcviku a jejich úloh v aplikaci – **jen desktop**, se
**zvláštním právem**. Důležité jsou vazby úlohy na **kategorii letadla** a **účel letu**,
musí být vidět **hierarchie** a to, **kde se úloha nabízí v novém letu** (zaškrtávátka).
Maketa: `docs/navrhy/osnovy-desktop.html` (skutečná data ze serveru 9. 10. 2026).

## 1. Dnešní stav a problém
- `lov_osnova (kod, nazev, poradi, platny, kategorie_id)` → `lov_uloha (…, osnova_id)` →
  vazba `lov_uloha_ucel (uloha_id, ucel_id)`; nabídka pohledem `v_uloha_nabidka`.
- **Osnova patří striktně k jedné kategorii** (upřesněno 9. 10. 2026) – všechny 4 osnovy
  jsou „Kluzák“. Některé úlohy kluzákové osnovy se ale létají i na **TMG** (II/10–12 a podle
  uvážení další) – dnes se nabízejí jen u letu kluzáku, u TMG ne. Kategorie osnovy dnes jde
  i prázdná („pro všechny“) – to už nebude.
- **Účely se zapínají u každé úlohy zvlášť** (výcvik, sólo, přezkoušení, normální) – beze změny.
- Úpravy jen přímo v databázi.

## 2. Datový model (změny)
```sql
-- osnova vždy právě jedné kategorie
ALTER TABLE lkkl.lov_osnova ALTER COLUMN kategorie_id SET NOT NULL;
-- úloha se dá letět „také na“ další kategorii (navíc ke kategorii své osnovy)
CREATE TABLE lkkl.lov_uloha_kategorie (
    uloha_id     bigint NOT NULL REFERENCES lkkl.lov_uloha,
    kategorie_id bigint NOT NULL REFERENCES lkkl.lov_kategorie,
    PRIMARY KEY (uloha_id, kategorie_id)
);  -- trigger: kategorie_id ≠ kategorie osnovy úlohy (ta platí vždy, neukládá se podruhé)
-- zvláštní právo na účtu
ALTER TABLE lkkl.ucet ADD COLUMN spravuje_osnovy boolean NOT NULL DEFAULT false;
```
Úloha se tedy letí na kategorii **své osnovy a na kategorie z `lov_uloha_kategorie`**.

**Kód a název bez opakování** (rozhodnuto 9. 10. 2026, migrace 040 – hotovo): `kod` osnovy
i úlohy je oficiální označení a zobrazuje se (CLAUDE.md bod 10 – evidenční číselník):

| | `kod` | `nazev` | text v aplikaci (pohled) |
|---|---|---|---|
| osnova | `IU` | Výcvik SPL (naviják a aerovlek) | `popis` = „IU – Výcvik SPL (naviják a aerovlek)“ |
| úloha | `8P` (jedinečný v osnově) | Přezkoušení před samostatnými lety | `oznaceni` = „IU/8P“, `popis` = „IU/8P Přezkoušení…“ |
- **Nabídka** `v_uloha_nabidka`: úloha × účel × kategorie (osnovy + „také na“), jen platná
  úloha i osnova (jako dnes); z ní průvodce i kontrola letu (`let_zkontrolovat`: úloha musí patřit k účelu
  a kategorii letadla; povinnost úlohy jen tam, kde nějaká existuje – beze změny pravidla).
- Vazba `lov_uloha_kategorie` hlídaná platností (`kontrola_platnosti`, db/031).
- **Audit** na `lov_osnova`, `lov_uloha`, `lov_uloha_ucel`, `lov_uloha_kategorie` (úpravy
  z aplikace i z databáze) s čitelnými popisky.
- II/10–12 „také na TMG“ – v editoru, nebo rovnou v migraci (rozhodnete).

## 3. Obrazovka (desktop)
Nabídka uživatele → Správa → **Osnovy a úlohy** (admin, nebo právo *spravuje osnovy*) →
**panel přes celou desku**. Na telefonu položka není.
- **Matice** vlevo – hierarchie osnova → úlohy:
  - řádek **osnovy** (sbalitelný): název, počet úloh, „+ úloha“; souhrnná zaškrtávátka
    (plné / prázdné / částečně) – klik nastaví všem úlohám osnovy; platná;
  - řádky **úloh**: pořadí ▲▼, název (např. „IU/4 Navijákové vzlety…“), zaškrtávátka
    **účel** (Normální · Výcvik · Sólo · Přezkoušení; u povinných „povinná“) a **lze letět
    i na** (jen jiné kategorie, než je kategorie osnovy – u kluzákové Letoun · TMG · UL), počet
    letů s úlohou, platná. Kategorie je **jen u osnovy** (v jejím řádku); úloha zůstává ve své
    osnově a u letu jiné kategorie se nabídne pod ní („II – Sportovní výcvik → II/10…“);
  - úloha bez účelu: oranžově „nenabízí se“.
  - Nová osnova se zakládá s kategorií (povinná).
- Vpravo **vybraná úloha**: **označení** (pevná předpona osnovy „II/“ + kód „10“) a **název**
  zvlášť (db/040), pod nimi výsledný text „II/10 TMG – vzlet…“ a štítek pásku „II/10“; přesun
  do jiné osnovy, smazat. Klik na řádek osnovy otevře stejně její označení, název a kategorii.
  Dále **náhled nového letu**:
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
1. **Kategorie osnovy + „také na“ u úlohy** (`lov_uloha_kategorie` jen s dalšími kategoriemi)
   – souhlas?
2. **Právo *spravuje osnovy*** – samostatné (doporučuji, např. vedoucí výcviku), nebo jen admin?
3. **Povinnost úlohy u účelu** (`lov_ucel.uloha_povinna` – dnes výcvik, sólo, přezkoušení):
   v editoru jen zobrazit (doporučuji), nebo i měnit?
4. II/10–12 přepnout na TMG už v migraci, nebo ručně v editoru?
