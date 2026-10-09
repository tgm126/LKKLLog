# Modul: typy přezkoušení (rozhodnuto a realizováno 9. 10. 2026 – db/041)

Zadání 9. 10. 2026: číselník typů přezkoušení podle podkladu `podklady/typy_prezkouseni.md`.
Navazuje na `podklady/prezkouseni.md` (kap. 6 a 7) a na rozhodnutí v `tabulky.md`: „u přezkoušení
typ přezkoušení“.

## 1. Rozhodnutí (9. 10. 2026)
1. **Samostatný číselník** `lov_prezkouseni` – let s účelem Přezkoušení má místo úlohy typ
   přezkoušení; typ patří k jedné kategorii a určuje, kdo ho smí provést.
2. **Rozsah:** teorie a angličtina ne (nejsou lety). Dál podle doporučení: přezkoušení před
   1. sólem zůstává úlohou osnovy (IU/8P, IA/8P, účel Výcvik); udržovací let a nový způsob
   vzletu jsou výcvik s instruktorem; MEP a IR klub nemá (jde kdykoli doplnit v datech).
3. **II/9P „Přezkoušení CLOUD“** → typ přezkoušení `PC-CLOUD` (kluzák, FE(S)) – návrh
   (uživatel neví): podle SFCL.215 se oprávnění k letům v oblacích při ztrátě rozlétanosti
   obnovuje přezkoušením s FE(S), stejně to říká poznámka k osnově (019 data); úloha II/9P
   se zruší (bez letů smazat, s lety zneplatnit).
4. **Oprávnění doplnit:** FIE(A) (ověření FI(A) a CRI(A)) a FE(S) pro ověření FI(S).
5. **Přejmenovat:** účel „Výcvik sólo“ → „Sólo pod dozorem“, funkce „Žák“ → „Pilot ve výcviku“.

## 2. Účely letu – revize (diskuse 9. 10. 2026)
Účely (normální, výcvik, sólo, přezkoušení; vlek z vazby) **zůstávají**:
- Předpisy (zápisník FCL.050 / SFCL.050, rozlétanost) pracují s **funkcí osoby**, ne s účelem;
  účel je klubová kategorie, podle které průvodce ukáže pole posádky a úlohu.
- **Vědomá redundance:** účel jde odvodit z funkcí v posádce (kontrola letu vyžaduje funkce
  přesně podle účelu). Nechává se – je to první volba v průvodci a váží se na něj role a úlohy.
- **PIC u přezkoušení zůstává examinátor** (podle AMC1 FCL.050 a AMC1 SFCL.050 zapisuje
  examinátor čas jako PIC a úspěšný přezkoušený také – `podklady/prezkouseni.md` kap. 7).
  Až se budou počítat hodiny PIC osoby, bude potřeba **výsledek přezkoušení** (jen úspěšné se
  počítá jako PIC) – zatím se nezavádí.
- **Výcvik vlekaře** na vlečném letu (vlečný let nemá účel) – jednou za 2 roky, zatím neřešit.
- **Vyhlídkové a technické lety** se neodlišují; cena se podle účelu neliší (určuje ji
  účetnictví podle typu členství).

## 3. Datový model
```sql
-- evidenční číselník: kod = označení typu, zobrazuje se (štítek pásku „PC-SEP“)
CREATE TABLE lkkl.lov_prezkouseni (
    id           bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kod          lkkl.kod    NOT NULL UNIQUE,
    nazev        lkkl.nazev  NOT NULL,
    poradi       lkkl.poradi NOT NULL,
    platny       lkkl.platny NOT NULL,
    kategorie_id bigint      NOT NULL REFERENCES lkkl.lov_kategorie
);
-- kdo smí přezkoušení provést (PIC = examinátor)
CREATE TABLE lkkl.lov_prezkouseni_opravneni (
    prezkouseni_id bigint NOT NULL REFERENCES lkkl.lov_prezkouseni,
    opravneni_id   bigint NOT NULL REFERENCES lkkl.lov_opravneni,
    PRIMARY KEY (prezkouseni_id, opravneni_id)
);
ALTER TABLE lkkl.let ADD COLUMN prezkouseni_id bigint REFERENCES lkkl.lov_prezkouseni;
CREATE VIEW lkkl.v_lov_prezkouseni AS   -- nabídka: platné, podle pořadí; popis „PC-SEP Přezkoušení…“
SELECT id, kod, nazev, poradi, kategorie_id, kod || ' ' || nazev AS popis
FROM lkkl.lov_prezkouseni WHERE platny ORDER BY poradi, nazev;
```
- **Kontrola letu** (`let_zkontrolovat`): typ přezkoušení **právě u účelu Přezkoušení** (jinde
  prázdný) a jeho kategorie = kategorie letadla. U přezkoušení se úloha nezadává:
  `lov_ucel.uloha_povinna` = false a vazby `lov_uloha_ucel` na Přezkoušení se zruší.
- **Platnost** (`kontrola_platnosti`) na `let.prezkouseni_id` a obou sloupcích vazby.
- **Nabídka examinátora** (PIC u přezkoušení): osoby s oprávněním z
  `lov_prezkouseni_opravneni` pro kategorii letadla (`lov_osoba_opravneni_kategorie`);
  pohled `v_osoba_prezkouseni (osoba_id, prezkouseni_id)`. **Role EXAMINATOR se smaže**
  (`lov_role` a její řádky v `lov_opravneni_role`) – kdo přezkušuje, je na jednom místě.
- **`v_let`**: `prezkouseni` (popis) a `prezkouseni_kod`. **Audit**: popisek sloupce
  `let.prezkouseni_id` a čitelná hodnota v `audit_hodnota` (historie letu). Číselník ani vazba
  audit nemají – jako ostatní číselníky bez editoru v aplikaci.
- **Kód s pomlčkou:** doména `lkkl.kod` připouští i `-` (označení PC-SEP, ST-LAPL-A).
- **Přejmenování** v datech struktury (`lov_ucel`, `lov_funkce` – názvy, kódy beze změny).
- Data zadává uživatel, mění se přímo v databázi; editor v aplikaci až podle potřeby.

## 4. Počáteční data (`041_prezkouseni_data.sql`)
| Kategorie | kod | nazev | Kdo provádí |
|---|---|---|---|
| Kluzák | ST-SPL | Zkouška dovednosti SPL | FE(S) |
| Kluzák | PC-SPL | Přezkoušení odborné způsobilosti SPL | FE(S) |
| Kluzák | PC-CLOUD | Přezkoušení pro lety v oblacích | FE(S) |
| Kluzák | AOC-FI-S | Ověření způsobilosti instruktora FI(S) | FE(S) – ověření FI(S) |
| TMG | ST-TMG | Zkouška dovednosti TMG | FE(S), FE(A) |
| TMG | PC-TMG | Přezkoušení odborné způsobilosti TMG | FE(S), FE(A), CRE(A) |
| Letoun | ST-LAPL-A | Zkouška dovednosti LAPL(A) | FE(A) |
| Letoun | ST-PPL-A | Zkouška dovednosti PPL(A) | FE(A) |
| Letoun | PC-LAPL-A | Přezkoušení odborné způsobilosti LAPL(A) | FE(A) |
| Letoun | PC-SEP | Přezkoušení odborné způsobilosti SEP (prodloužení, obnova) | FE(A), CRE(A) |
| Letoun | AOC-FI-A | Ověření způsobilosti instruktora FI(A), CRI(A) | FIE(A) |
| UL | ST-ULL | Závěrečná zkouška pilota ULL | inspektor ULL |
| UL | PC-ULL | Ověření praktických dovedností pilota ULL | inspektor ULL |
| UL | ST-ULL-CTR | Zkouška pro řízené lety VFR | inspektor ULL |
| UL | ST-ULL-VLEK | Zkouška kvalifikace vlekař ULL | inspektor ULL |
| UL | AOC-ULLI | Přezkoušení instruktora ULL | inspektor ULL |

Předpony: **ST** = zkouška dovednosti, **PC** = přezkoušení odborné způsobilosti, **AOC** =
ověření způsobilosti instruktora.

Nová oprávnění (`lov_opravneni`, data): `FIE_A` „FIE(A) – examinátor instruktorů letounů“
(letoun, TMG) a `FE_S_FI` „FE(S) – ověření instruktorů FI(S)“ (kluzák, TMG); k rolím v letu
neopravňují (jen k typům přezkoušení).

## 5. Obrazovky
- **Průvodce (mobil) a panel nového letu (desktop):** u účelu Přezkoušení je místo bloku Úloha
  blok **Přezkoušení** – seznam „kód · název“ typů pro kategorii letadla (povinný, jen když
  pro kategorii nějaký typ existuje). Pole examinátora nabídne osoby, které zvolený typ smí
  (před volbou typu ty, které smí některý typ na kategorii); „Hledat…“ jako dosud.
- **Pásek a deník:** kód typu ve štítku na pozici úlohy (u letu je buď úloha, nebo typ).
- **Detail letu:** typ přezkoušení jde změnit jako úloha.
- Štítky „Sólo“ / „sólo“ zůstávají; popisek pole „Žák (PIC)“ u sóla → „Pilot (PIC)“.
- Příručka: přezkoušení s typem, nové názvy.

## 6. Realizace (9. 10. 2026)
- `db/041_prezkouseni.sql`: struktura, počáteční typy a oprávnění FIE(A), FE(S) – ověření FI(S)
  (jednorázově, aby přišly na server), přejmenování, kontrola letu, pohledy, zrušení role
  EXAMINATOR a vazeb úloh na Přezkoušení, převod letů. `041_prezkouseni_data.sql` = totéž
  naplnění pro novou databázi (kategorie a oprávnění tam vznikají až daty).
- Server 9. 10. 2026: jediný let s účelem Přezkoušení (úloha II/9P) → PC-CLOUD, úloha II/9P
  smazána; zkouška na kopii serverových dat prošla.
- Rozhraní: nabídky (`prezkouseni`, u osob `prezkouseni` = id typů, které smí provést),
  založení a úprava letu (`prezkouseni_id`), pásek a detail (`prezkouseni`, `prezkouseni_kod`).
- Obrazovky: blok Přezkoušení v kroku 2 průvodce (pod účelem, před posádkou – examinátor se
  pak nabízí podle typu) a v levém sloupci panelu desktopu; v detailu pole Přezkoušení.
- Testy: `backend/tests/test_prezkouseni.py`, klikací `e2e/akce.spec.ts` (přezkoušení).
