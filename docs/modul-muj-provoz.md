# Modul: můj provoz (letiště a osoby v provozu na dnešek)

Navrženo a odsouhlaseno 7. 10. 2026, skript `db/026_muj_provoz.sql`. Maketa
`docs/navrhy/muj-provoz-mobil.html` (mobil; desktop později).

## 1. Účel
Aeroklub se občas přesune jinam (např. na týden na tábor) a na letišti nebývají všichni
členové. Každý uživatel si proto může **jen pro sebe, na svém zařízení a jen na dnešek**
nastavit:
- **letiště** – místo, kde dnes létá (výchozí je domovské letiště z číselníku, LKKL); je
  výchozím místem přistání nového letu a místem vzletu u letadla bez evidovaného přistání
  (jinak se startuje z posledního místa přistání letadla – 8. 10. 2026);
- **osoby v provozu** – kdo je dnes na letišti; slouží jako filtr nabídky osob v posádce.

Nic se neblokuje: „Hledat…“ v posádce dál hledá mezi všemi osobami a místo letu jde vždy
změnit. Nastavení ostatních uživatelů se nemění.

## 2. Platnost
- Nastavení patří **relaci** (= přihlášené zařízení), ne účtu: na jiném telefonu se stejným
  účtem neplatí.
- Platí **jen pro den, kdy bylo uloženo** (den v UTC jako přehled letů, tj. do půlnoci UTC –
  v létě do 2:00 místního času). Další den je letiště zase domovské a filtr osob prázdný.
- Odhlášením nebo vypršením relace (30 dní nečinnosti) zanikne.

## 3. Obrazovky (mobil)
- **Nabídka uživatele** (kolečko s iniciálami): pod jménem nový oddíl **Můj provoz · dnes**
  se dvěma řádky – *Letiště* (kód a název, „domovské“) a *Osoby v provozu* (počet, „všechny“).
  Ťuknutí otevře obrazovku výběru. Pod tím beze změny Režim zobrazení a Odhlásit.
- **Letiště pro dnešek:** horní lišta ← „Letiště pro dnešek“; nahoře domovské letiště,
  hledání podle kódu nebo názvu, čipy letišť (jako výběr místa v průvodci). Ťuknutí uloží
  a vrátí zpět.
- **Osoby v provozu:** horní lišta ← „Osoby v provozu“ a vpravo počet vybraných; hledání,
  segmenty *Vybrané / Všechny*, řádky aktivních osob se zaškrtávátkem (uloží se hned).
  Dole *Zrušit výběr* (= bez filtru, nabízí se všichni).
- **Hlavička:** je-li dnes jiné než domovské letiště, vpravo v řádku menu **oranžový štítek
  s kódem letiště** (upozornění, že platí jiné místo; vedle případného štítku „Jen ke čtení“).
  Datum v hlavičce zůstane celé i se dnem v týdnu a rokem (8. 10. 2026 – dřív byl štítek
  před datem a datum se zkracovalo); sluneční časy jsou pro toto letiště. Ťuknutí na štítek
  otevře výběr letiště.
- **Posádka v průvodci a v detailu letu:** je-li vybraná aspoň jedna osoba v provozu, rychlá
  volba nabízí jen je: kdo roli smí podle oprávnění (instruktor, dozor, examinátor, vlekař),
  a když z nich nikdo, Já, nedávno létající a ostatní osoby v provozu (u pilota a žáka vždy
  tak). Nad volbou drobně „jen osoby v provozu (12) · ostatní přes Hledat…“. „Hledat…“
  hledá mezi všemi. Bez výběru se nabízí jako dnes.

## 4. Co letiště změní
| Kde | Dnes (domovské) | S nastaveným letištěm |
|---|---|---|
| Hlavička | sluneční časy LKKL | štítek s kódem, sluneční časy zvoleného letiště |
| Varování „konec dne“ u pásků | podle TE domovského | podle TE zvoleného letiště |
| Nový let, proběhlý let | místo vzletu a přistání = domovské | = zvolené letiště (server ho uloží výslovně) |
| Přistání z pásku | místo přistání = domovské | = zvolené letiště |
| Pásky | místo se ukazuje, když není domovské | místo se ukazuje, když není **moje** letiště |
| Seznam letů dne | všechny lety klubu | beze změny – všechny lety klubu (rozhodnuto 7. 10. 2026) |

Databáze dál doplňuje domovské letiště tam, kde místo nikdo nezadal (zápis přímo v databázi);
server místo z aplikace ukládá vždy výslovně (nový let, proběhlý let, přistání z pásku,
doplněné přistání v detailu).

## 5. Data
Provozní tabulky (smažou se spolu s relací při odhlášení a úklidu prošlých relací), bez auditu –
nastavení zařízení, ne údaje letu (místo letu se zapisuje do letu a to audit má).

```sql
CREATE TABLE lkkl.relace_provoz (
    relace_id  text   PRIMARY KEY REFERENCES lkkl.relace,
    den        date   NOT NULL,                        -- pro který den (UTC) nastavení platí
    letiste_id bigint REFERENCES lkkl.lov_letiste      -- prázdné = domovské
);
CREATE TABLE lkkl.relace_provoz_osoba (                        -- osoby v provozu; žádný řádek = bez filtru
    relace_id  text   NOT NULL REFERENCES lkkl.relace_provoz,
    osoba_id   bigint NOT NULL REFERENCES lkkl.lov_osoba,
    PRIMARY KEY (relace_id, osoba_id)
);
```
- Nastavení s jiným dnem než dnešním se nebere v úvahu; první uložení v novém dni ho přepíše
  (a smaže osoby).
- Odhlášení, zablokování, změna hesla i úklid prošlých relací mažou relace jednou funkcí
  serveru `smazat_relace` – nejdřív `relace_provoz_osoba` a `relace_provoz` (cizí klíče bez
  kaskádového mazání).
- Pohledy `v_relace_letiste` (relace → dnešní letiště: zvolené, jinak domovské; kód, název,
  souřadnice) a `v_relace_osoba` (dnešní osoby v provozu) – jinde se pravidlo „platí jen
  dnes“ neopakuje.
- Tabulka osob se jmenuje `relace_provoz_osoba` (jméno `relace_osoba` má už index na
  `relace.osoba_id`).

## 6. Rozhraní (API)
| Volání | Co |
|---|---|
| `GET /api/muj-provoz` | dnešní nastavení relace: letiště (id, kód, název, domovské) a osoby v provozu (id) |
| `POST /api/muj-provoz/letiste` | `{letiste_id}` – prázdné = domovské |
| `POST /api/muj-provoz/osoby` | `{osoba_id, ma}` – přidat / odebrat |
| `POST /api/muj-provoz/osoby/zrusit` | bez filtru – nabízejí se všichni |
| `GET /api/den`, `GET /api/lety`, akce letu | letiště relace místo domovského (sluneční časy, varování, výchozí místa, zobrazení místa) |

## 7. Testy
Server: platnost jen dnes (včerejší nastavení se neuplatní), výchozí místa nového letu
a přistání, sluneční časy, odhlášení smaže nastavení, cizí relace nastavení nevidí.
Klikací: nastavení letiště → štítek v hlavičce a místo u nového letu; osoby v provozu →
rychlá volba jen z nich, „Hledat…“ najde i ostatní; zrušení výběru.
