# Modul: správa systému (admin)

Zadání 8. 10. 2026: admin smaže lety celého dne z aplikace (dosud jen procedurou v databázi)
a přepne nastavení systému. Jen admin, ne v relaci jen ke čtení (server to hlídá).

## 1. Nabídka uživatele
Oddíl **Správa** (jen admin, ne jen ke čtení) nad Odhlásit: **Smazat lety dne…** ·
**Nastavení**. Obě obrazovky jako Můj provoz – na mobilu celá obrazovka, na desktopu sloupec
uprostřed; Zpět vrací, odkud admin přišel.

## 2. Smazat lety dne
- **Kalendář po měsících** (‹ říjen 2026 ›, týden od pondělí). Dny s lety jsou **tučně**
  a pod číslem dne je počet letů; dny bez letů jsou šedé a nejde je vybrat. Otevře se na
  měsíci posledního dne s lety. Dnešek je orámovaný.
- Klik na den s lety → **potvrzení** (dialog): „Smazat lety čtvrtek 7. 10. 2026?“ – počet
  letů, že se smažou ve všech stavech (i ve vzduchu a naplánované) s posádkou a T&G, u vleku
  obě poloviny; nejde vrátit, v historii zůstane záznam o smazání. Tlačítka **Smazat N letů**
  (červeně) · Zpět.
- Smazání volá proceduru `lkkl.smazat_lety_dne(den)` (db/033) – stejné pravidlo jako přímo
  v databázi; audit zapíše, kdo mazal. Po smazání se kalendář obnoví a pod ním je potvrzení
  „Smazáno N letů dne …“.
- Den letu jako všude: datum vzletu, u nevzlétnutého letu datum založení (UTC).

## 3. Nastavení
Blok **Provoz**: zaškrtávátko **Testovací provoz** („žlutý pruh nahoře“) –
`lkkl.nastaveni.testovaci_provoz` (db/034); uloží se hned, pruh se změní u všech do minuty
(aplikace se ptá každou minutu). Další nastavení přibudou jako další sloupce tabulky.

## 4. Rozhraní (jen admin)
| Volání | Co dělá |
|---|---|
| `GET /api/sprava/dny-s-lety` | dny s lety a jejich počet (`v_let` po dnech) |
| `POST /api/sprava/smazat-den` `{den}` | `CALL lkkl.smazat_lety_dne(den)`, vrátí počet |
| `GET /api/sprava/nastaveni` | nastavení systému |
| `POST /api/sprava/nastaveni` `{testovaci_provoz}` | změna nastavení |

## 5. Testy
Server: jen admin (ostatní 403, jen ke čtení 403), dny s lety, smazání dne a počet, nastavení.
Klikací (mobil): položky v nabídce jen u admina, kalendář s tučným dnem, potvrzení a smazání,
nastavení testovacího provozu.
