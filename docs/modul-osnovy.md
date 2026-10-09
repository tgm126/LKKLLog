# Modul: osnovy, úlohy a typy přezkoušení (realizováno 9. 10. 2026 – db/042; otevřený bod 1)

Zadání 9. 10. 2026: editace osnov výcviku a jejich úloh v aplikaci – **jen desktop**, se
**zvláštním právem**. Důležité jsou vazby úlohy na **kategorii letadla** a **účel letu**,
musí být vidět **hierarchie** a to, **kde se úloha nabízí v novém letu** (zaškrtávátka).
Maketa: `docs/navrhy/osnovy-desktop-v2.html` (skutečná data ze serveru 9. 10. 2026, po 041;
předchozí `osnovy-desktop.html`).

**Revize po typech přezkoušení (9. 10. 2026, db/041, `modul-prezkouseni.md`):** úlohy se
u přezkoušení nenabízejí – místo nich je **typ přezkoušení** (`lov_prezkouseni`, jedna
kategorie, kdo smí provést = `lov_prezkouseni_opravneni`). Editor proto spravuje **dvě věci**:
osnovy s úlohami (výcvik, sólo, normální let) a typy přezkoušení (kap. 3a).

## 1. Dnešní stav a problém
- `lov_osnova (kod, nazev, poradi, platny, kategorie_id)` → `lov_uloha (…, osnova_id)` →
  vazba `lov_uloha_ucel (uloha_id, ucel_id)`; nabídka pohledem `v_uloha_nabidka`.
- **Osnova patří striktně k jedné kategorii** (upřesněno 9. 10. 2026) – všechny 4 osnovy
  jsou „Kluzák“. Některé úlohy kluzákové osnovy se ale létají i na **TMG** (II/10–12 a podle
  uvážení další) – dnes se nabízejí jen u letu kluzáku, u TMG ne. Kategorie osnovy dnes jde
  i prázdná („pro všechny“) – to už nebude.
- **Účely se zapínají u každé úlohy zvlášť** – jen výcvik, sólo a normální let; přezkoušení
  od 041 úlohy nemá (II/9P se stala typem PC-CLOUD). „Přezkoušení“ před sólem (IU/8P, IA/8P)
  zůstává úlohou výcviku – dělá ho instruktor.
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
-- zvláštní právo na účtu: osnovy, úlohy i typy přezkoušení
ALTER TABLE lkkl.ucet ADD COLUMN spravuje_vycvik boolean NOT NULL DEFAULT false;
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
- **Audit** na `lov_osnova`, `lov_uloha`, `lov_uloha_ucel`, `lov_uloha_kategorie`,
  `lov_prezkouseni` a `lov_prezkouseni_opravneni` (úpravy z aplikace i z databáze) s čitelnými
  popisky – číselníky s editorem v aplikaci audit mají.
- II/10–12 „také na TMG“ – v editoru, nebo rovnou v migraci (rozhodnete).

## 3. Obrazovka (desktop)
Nabídka uživatele → Správa → **Výcvik** (admin, nebo právo *spravuje výcvik*) →
**panel přes celou desku**. Na telefonu položka není.
- **Matice** vlevo – hierarchie osnova → úlohy:
  - řádek **osnovy** (sbalitelný): název, počet úloh, „+ úloha“; souhrnná zaškrtávátka
    (plné / prázdné / částečně) – klik nastaví všem úlohám osnovy; platná;
  - řádky **úloh**: pořadí ▲▼, název (např. „IU/4 Navijákové vzlety…“), zaškrtávátka
    **účel** (Normální · Výcvik · Sólo; u povinných „povinná“) a **lze letět
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

## 3a. Typy přezkoušení (revize 9. 10. 2026)
Ve stejném panelu přepínač nahoře **Osnovy a úlohy | Typy přezkoušení**.
- **Tabulka** seskupená podle kategorie (Kluzák · TMG · Letoun · UL): pořadí ▲▼, **kód**
  (PC-SEP) a **název**, zaškrtávátka **kdo smí provést** – jen oprávnění, která se pro tu
  kategorii vydávají (`lov_opravneni_kategorie`; u kluzáku FE(S), FE(S) – ověření FI(S)…),
  počet letů, platný. Typ bez oprávnění: oranžově „nikdo ho nesmí provést“.
- Vpravo **vybraný typ**: kód, název, kategorie (u použitého typu jen pro čtení – lety by
  přestaly sedět na kategorii letadla), smazat. Dále **náhled**: kdo se pilotovi nabídne jako
  examinátor (osoby s oprávněním pro kategorii, `v_osoba_prezkouseni`) – hned je vidět, když
  oprávnění osob chybí (dnes na serveru jen FE(S) na kluzácích).
- Kategorie je u typu jedna (bez „lze letět i na“) – TMG má vlastní typy.
- Náhled nového letu v části osnov ukáže u účelu Přezkoušení místo úloh blok Přezkoušení.

## 3b. Realizace (9. 10. 2026)
- `db/042_vycvik.sql`: právo `ucet.spravuje_vycvik`, `lov_osnova.kategorie_id` povinná,
  trigger `vycvik_kontrola` (pravidla kap. 4), audit pěti tabulek (bez pořadí).
  `lov_uloha_kategorie` („lze letět i na“) zatím ne – bod 1 je otevřený.
- Server `backend/app/vycvik.py` (`/api/vycvik`, každá změna vrátí celý stav), frontend
  `frontend/src/vycvik/` (panel `/vycvik` přes celou desku, položka Správa → Výcvik jen na
  desktopu), právo v detailu osoby.
- Testy: `backend/tests/test_vycvik.py`, klikací `frontend/e2e/vycvik.spec.ts`.
- Nabídka examinátora (náhled) se počítá z `v_osoba_prezkouseni` – oprávnění osob se mění
  v detailu osoby.

## 4. Pravidla
- **Kód** (`kod`) zadává uživatel – je to označení a zobrazuje se (evidenční číselník, db/040
  a 041): u osnovy „IU“, u úlohy „8P“ (jedinečný v osnově), u typu přezkoušení „PC-SEP“
  (velká písmena, číslice, `_`, `-`).
- **Smazat** jde jen úlohu bez letů (s vazbami), osnovu bez úloh a typ přezkoušení bez letů;
  použité jen **zneplatnit** – ve starých letech zůstane, nikde se nenabízí.
- Přesun úlohy do jiné osnovy jde (lety odkazují na úlohu, ne na osnovu).
- Pořadí ▲▼ v osnově (`poradi`), osnovy mezi sebou (▲▼ u vybrané osnovy), typy
  přezkoušení v rámci kategorie.
- **Co by rozbilo staré lety, nejde** (databáze, `vycvik_kontrola`): změnit kategorii osnovy
  nebo typu přezkoušení, které jsou v letech; přesunout použitou úlohu do osnovy jiné
  kategorie; odebrat úloze účel, se kterým se letěla. Typ přezkoušení smí provést jen
  oprávnění vydávané pro jeho kategorii (při změně kategorie nepoužitého typu ostatní
  odpadnou).
- Právo *spravuje výcvik* přiděluje admin v detailu osoby (jako ostatní práva); server hlídá.

## 5. Testy
Server: práva (403), převod kategorií (II/10–12), nabídka podle účelu a kategorie, kontrola
letu s novou vazbou, smazání jen nepoužitého, audit; typy přezkoušení – oprávnění jen pro
kategorii typu, kategorie použitého typu nejde změnit. Klikací (desktop): matice, souhrnné
zaškrtnutí osnovy, náhled, pořadí, nová úloha, zneplatnění, typ přezkoušení a jeho oprávnění.

## 6. Rozhodnutí
1. **Kategorie osnovy + „lze letět i na“ u úlohy** (`lov_uloha_kategorie` jen s dalšími
   kategoriemi; úloha zůstává ve své osnově) – **otevřené** (9. 10. 2026 stále), uživatel
   ještě zjišťuje, jak je to s úlohami na TMG. Ostatní části editoru na tom nezávisí.
2. **Právo *spravuje výcvik*** (`spravuje_vycvik`) – **samostatné** na účtu, **jedno** pro
   osnovy, úlohy i typy přezkoušení (rozhodnuto 9. 10. 2026; přiděluje admin, např.
   vedoucímu výcviku).
3. **Povinnost úlohy u účelu** (`lov_ucel.uloha_povinna`) – v editoru **jen zobrazit**
   (rozhodnuto 9. 10. 2026; mění se v databázi).
4. **II/10–12 „lze letět i na TMG“** – nastaví se **ručně v editoru** (rozhodnuto 9. 10. 2026),
   migrace jen připraví vazbu.
5. **Typy přezkoušení** – ve **stejném panelu** přepínačem (rozhodnuto 9. 10. 2026).
6. **Kdo smí provést** – zaškrtávátky **v editoru** typů (rozhodnuto 9. 10. 2026).
