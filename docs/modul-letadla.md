# Modul: letadla (číselník letadel)

Navrženo a odsouhlaseno 7. 10. 2026 (varianta A – vlastní právo). Mobil; desktop později.
Zatím jen **přepínač mimo provoz**; další úpravy letadel (typ, vlečné, soukromé, max. doba
letu, termíny) přijdou s rozšířením číselníku.

## 1. Rozsah
- **Letadla** ve Správě nabídky uživatele (od 9. 10. 2026, dřív záložka) – jen pro právo
  **spravuje letadla** (a admina, který má všechna
  práva automaticky). Server právo hlídá u každého požadavku.
- **Seznam letadel** po kategoriích (pořadí kategorie → typ → rejstřík): rejstřík, pod ním
  typ (případně „soukromé“, „mimo provoz“), vpravo zaškrtávátko = **mimo provoz**. Zaškrtnutí se
  uloží hned, oznámení dole („OK-6722 mimo provoz“ / „zpět v provozu“).
- Mimo provoz = letadlo se **nenabízí pro nové lety** (v průvodci je vidět, ale nejde vybrat);
  stará data zůstávají, naplánované lety se nemění.

## 2. Data
- `lov_letadlo.mimo_provoz` (db/013) – beze změny; změny zapisuje audit („mimo provoz ne → ano“).
- `ucet.spravuje_letadla boolean NOT NULL DEFAULT false` (db/029), v auditu „spravuje letadla“;
  přiděluje jen admin (detail osoby → Účet a přihlášení).

## 3. Rozhraní (API)
| Volání | Kdo | Co |
|---|---|---|
| `GET /api/letadla` | správce letadel | všechna letadla: rejstřík, typ, kategorie, soukromé, mimo provoz |
| `POST /api/letadla/{id}/mimo-provoz` | správce letadel | `{mimo_provoz}` – vyřadit / vrátit do provozu |
| `GET /api/ja` | přihlášený | práva i se `spravuje_letadla` (admin = vše) |

## 4. Testy
Server: bez práva 403, správce letadel smí, právo přiděluje jen admin, přepnutí mimo provoz
a zápis do auditu, neexistující letadlo 404. Klikací: vyřazené letadlo nejde v průvodci
vybrat, vrácení do provozu.
