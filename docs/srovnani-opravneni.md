# Srovnání: stávající model oprávnění (021–022) × návrh (`navrh-opravneni.md`)

> Větev `navrh-opravneni`, 7. 10. 2026. Data ze serveru načtena týž den (jen čtení).

## 1. Objekty databáze

| Objekt | Dnes (021, 022) | Návrh | Změna |
|---|---|---|---|
| `lov_role` | – (role = dvojice účel + funkce opakovaná u každého oprávnění) | 4 role: INSTRUKTOR, DOZOR, EXAMINATOR, VLEKAR → účel + funkce | **nová tabulka** (kódy ve skriptu struktury) |
| `lov_opravneni` | standard číselníku + `omezene`; zvláštní řádky FI_S_OMEZENY, FI_A_OMEZENY | jen standard číselníku | **pryč** sloupec `omezene` a řádky `*_OMEZENY` |
| `lov_opravneni_kategorie` | pro které kategorie oprávnění **platí**; bez řádku = **všechny** (VLEKAR) | pro které kategorie se oprávnění **smí vydat**; bez řádku = **žádná** | změna významu; VLEKAR dostane LETOUN, UL |
| `lov_opravneni_role` | `id`, `opravneni_id`, `ucel_id` (NULL = vlek), `funkce_id`, UNIQUE NULLS NOT DISTINCT | `opravneni_id`, `role_id`, PK z obou | **přestavba** (umělý klíč a NULL v klíči pryč) |
| `lov_osoba_opravneni` | `osoba_id`, `opravneni_id` | + `omezene` | **nový sloupec** |
| `lov_osoba_opravneni_kategorie` | – (osoba má oprávnění vždy pro všechny jeho kategorie) | pro které kategorie ho osoba má; 2 složené FK | **nová tabulka** + audit |
| `v_osoba_smi` | osoba, účel, funkce, kategorie (prázdná = všechny) | osoba, **role**, účel, funkce, kategorie (vždy vyplněná) | přestavba pohledu |
| `v_osoba_opravneni` | osoba + výčet oprávnění | osoba + oprávnění s kategoriemi a omezením | úprava pohledu |
| `v_lov_opravneni` | standard | standard | beze změny |
| audit | trigger na `lov_osoba_opravneni`, popisky | + trigger a popisky na nové tabulce, `kategorie_id` a `omezene` v čitelné historii | doplnění |

**Co se zjednoduší:** role je zapsaná jednou (dnes se stejné tři řádky opakují u 10 oprávnění),
zmizí NULL v jedinečném klíči a dva „falešné“ druhy oprávnění, kategorie má jeden význam.
**Co přibude:** jedna vazební tabulka u osoby a jeden malý číselník.

## 2. Data na serveru (stav 7. 10. 2026)

| Oprávnění | Kategorie | Role dnes | Osob | Návrh: role | Návrh: převod osob |
|---|---|---|---|---|---|
| FI(S) | KLUZAK, TMG | výcvik, dozor, **přezkoušení** | 7 | instruktor, dozor | 7 × (KLUZAK, TMG) – **TMG odškrtáš**, kdo ho nemá |
| FI(S) omezený | KLUZAK, TMG | výcvik, dozor, přezkoušení | 0 | – (řádek zanikne) | – |
| FE(S) | KLUZAK, TMG | **výcvik, dozor**, přezkoušení | 1 | examinátor | 1 × (KLUZAK, TMG) |
| FI(A) | LETOUN, TMG | výcvik, dozor, **přezkoušení** | 3 | instruktor, dozor | 3 × (LETOUN, TMG) |
| FI(A) omezený | LETOUN, TMG | výcvik, dozor, přezkoušení | 0 | – (řádek zanikne) | – |
| CRI(A) | LETOUN, TMG | výcvik, dozor, **přezkoušení** | 0 | instruktor, dozor | – |
| FE(A), CRE(A) | LETOUN, TMG | **výcvik, dozor**, přezkoušení | 0 | examinátor | – |
| Instruktor ULL | UL | výcvik, dozor, **přezkoušení** | 2 | instruktor, dozor | 2 × UL |
| Inspektor ULL | UL | **výcvik, dozor**, přezkoušení | 0 | examinátor | – |
| Vlekař | **všechny** | vlek | 7 | vlekař | 7 × (LETOUN, UL) |

Tučně = role, která podle návrhu odpadne. Celkem 11 osob s oprávněním, 20 řádků převodu.
Převod je mechanický a nic neztratí: každá osoba dostane všechny kategorie, pro které se její
oprávnění smí vydat (= dnešní chování). Upřesnění (kdo nemá TMG) je pak tvoje ruční práce.

## 3. Co uvidí uživatelé (změna chování)

1. **Přezkoušení** – v rychlé volbě examinátora budou jen examinátoři (dnes i 7 FI(S), 3 FI(A)
   a 2 instruktoři ULL). Na serveru je dnes examinátor jen 1 (FE(S)) – u přezkoušení na
   letounu a UL tedy rychlá volba nikoho nenajde a nabídne zálohu (Já, nedávní); hledání
   funguje jako dnes.
2. **Výcvik a dozor** – FE(S) bez FI(S) se přestane nabízet jako instruktor (u 1 osoby
   ověřit, zda má i FI(S)).
3. **TMG** – hned po převodu stejné jako dnes; po odškrtnutí TMG u instruktorů bez práv TMG
   se na TMG nabídnou jen ti správní.
4. **Vlekař** – dnes se nabízí u vlečného letu na čemkoli, po převodu na letounu a UL
   (vlečná jsou letouny, takže v praxi beze změny).
5. **Detail osoby** – oprávnění se zaškrtávají **po kategoriích** (skupina Kluzák: FI(S),
   FE(S)…; skupina Motorový kluzák: FI(S), FI(A)…), „omezený“ je vlastnost zaškrtnutého
   instruktora, ne samostatná položka. Potřebuje úpravu makety `osoby-mobil.html` dřív než kód.

## 4. Dopad na aplikaci

| Část | Změna | Rozsah |
|---|---|---|
| `db/024_*.sql` | migrace podle kap. 5 | střední |
| `backend/app/lety.py` (nabídky osob) | bez změny dotazu (pohled vrací stejné sloupce + `role`) | malý |
| `backend/app/osoby.py` | oprávnění osoby jako seznam {oprávnění, kategorie[], omezené}; zápis po kategoriích a přepnutí omezení; číselník s povolenými kategoriemi | střední |
| `frontend/src/lety/Volby.tsx` | `smi()` bez větve „kategorie prázdná = všechny“ | malý |
| `frontend/src/osoby/*` | skupiny = jednotlivé kategorie, zaškrtávátko = (oprávnění, kategorie), přepínač „omezený“; štítky v seznamu | střední |
| testy | `test_osoby`, `test_akce` (nabídky), e2e `osoby`, příprava e2e dat | střední |
| dokumentace | `tabulky.md`, `modul-osoby.md`, `modul-lety.md`, maketa osob | malý |
| `db/021_opravneni_data.sql` | počáteční naplnění v novém tvaru (pro nové databáze) | malý |

## 5. Migrace `024` (náčrt pořadí – zachová data)

1. `lov_role` + 4 řádky (struktura – kódy používá program).
2. `lov_opravneni_role`: přidat `role_id`, doplnit podle (účel, funkce) z `lov_role`, odebrat
   `id`, `ucel_id`, `funkce_id`, PK (`opravneni_id`, `role_id`).
3. Opravit role podle dohody: přezkoušení jen examinátorům, výcvik a dozor jen instruktorům
   (podle kódů FI_S, FE_S…; na serveru existují).
4. `lov_osoba_opravneni.omezene`; osoby s `*_OMEZENY` převést na základní oprávnění
   s `omezene = true` (dnes 0 osob); smazat řádky `*_OMEZENY` a jejich vazby;
   `lov_opravneni` bez `omezene`.
5. VLEKAR → `lov_opravneni_kategorie` (LETOUN, UL).
6. `lov_osoba_opravneni_kategorie` + naplnění (osoba × všechny povolené kategorie
   oprávnění), audit trigger, popisky, `audit_hodnota` pro `kategorie_id`, `audit_akce`.
7. Pohledy `v_osoba_smi`, `v_osoba_opravneni` znovu.

Před nasazením: záloha serveru (`pg_dump`), migraci vyzkoušet lokálně **na kopii serverových
dat** (obnova zálohy do pomocné databáze), porovnat `v_osoba_smi` před a po.

## 6. Návrat

- **Teď:** jen dokumenty ve větvi `navrh-opravneni`; zahození = smazat větev.
- **Při realizaci:** kód i skript `024` ve stejné větvi, do `main` až po tvém vyzkoušení.
- **Po nasazení:** strukturu zpět nevracíme skriptem (byl by to „záplatový“ krok), ale
  obnovou zálohy serveru pořízené těsně před nasazením (data osob se mezitím mění jen
  ručně, takže ztráta je nanejvýš pár zaškrtnutí).

## 7. K rozhodnutí

1. Opravu rolí (kap. 5 bod 3) dát přímo do migrace `024` (doporučuji – je dohodnutá a
   jednorázová), nebo ji provedeš ručně v databázi?
2. Začít úpravou makety osob (zaškrtávání po kategoriích + omezení) a pak kód?
