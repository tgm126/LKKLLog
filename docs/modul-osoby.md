# Modul: osoby (správa osob a jejich nastavení)

Navrženo a odsouhlaseno 7. 10. 2026. Makety `docs/navrhy/osoby-mobil.html` a pro oprávnění
`osoby-mobil-v2.html` (varianta B; mobil, desktop později). První funkce aplikace závislá na
právu. Model oprávnění: `docs/navrh-opravneni.md`.

## 1. Rozsah
- Záložka **OSOBY** v menu – jen pro osoby s právem **spravuje osoby** (a admina).
- **Seznam osob:** hledání (jméno, e-mail, telefon, číslo člena), filtr Aktivní / S účtem /
  Neaktivní / Vše; u osoby telefon a značky (admin, správce, oprávnění, bez účtu, zablokován,
  externí). Dole „+ Nová osoba“.
- **Detail osoby:** údaje (ťuknutím upravit), člen klubu, aktivní; účet a přihlášení
  (smí se přihlásit, práva, odkaz pro nastavení hesla, přihlásit se jako); oprávnění po
  kategoriích letadel; historie změn z auditu.
- **Oprávnění** (db/024): řádek = oprávnění z číselníku, pod názvem čipy kategorií, pro které
  se smí vydat (zapnutý = osoba ho pro ni má). Zapnutí první kategorie oprávnění přidá,
  vypnutí poslední ho odebere. U instruktora, který oprávnění má, čip **omezený** (pod
  dohledem; oranžově, nabídku neovlivní). Nepoužitá oprávnění šedě. V seznamu osob jen
  zkratka oprávnění (omezení ne).
- **Nová osoba:** jméno, příjmení, e-mail, telefon, číslo člena, člen klubu.
- **Mazání osob není** – osoba se jen přepne na neaktivní (nenabízí se v letech, nepřihlásí se).

## 2. Práva
Práva se přidělují konkrétním osobám (sloupce v `ucet`); **admin má automaticky všechna**.

| Právo | Smí |
|---|---|
| `spravuje_osoby` (nové, db/023) | seznam a detail osob, nová osoba, úprava údajů, člen, aktivní, oprávnění; založit účet (smí se přihlásit), zablokovat / povolit účet (ne účet admina), odkaz pro nastavení hesla |
| `smi_odblokovat` | odblokovat účet zablokovaný po chybných heslech |
| `spravuje_letadla` (db/029) | záložka Letadla: mimo provoz (`docs/modul-letadla.md`) |
| `admin` | vše; navíc přiděluje práva (admin, smí odblokovat, spravuje osoby) a smí „přihlásit se jako“ |

Pravidla (hlídá server, ne jen skrytím tlačítek): sám sobě nikdo nevypne „aktivní“ ani
nezablokuje účet; admin si neodebere admina; účet admina smí měnit jen admin.

## 3. Data
- `lov_osoba` – beze změny (jméno, příjmení, e-mail, telefon, číslo člena, člen, aktivní –
  od 031 sloupec `platny` podle standardu platnosti, v aplikaci dál „aktivní“).
  Telefon se ukládá jako `+420…` (server převede „602 123 456“ i „00420…“), zobrazuje se
  po trojicích.
- `ucet.spravuje_osoby boolean NOT NULL DEFAULT false` (db/023), v auditu „spravuje osoby“.
- `lov_osoba_opravneni` (+ `omezene`) a `lov_osoba_opravneni_kategorie` – oprávnění osob
  po kategoriích (db/021, 024).

## 4. Rozhraní (API)
| Volání | Kdo | Co |
|---|---|---|
| `GET /api/osoby` | správce osob | osoby s účtem a oprávněními (kategorie, omezené) + číselník oprávnění (povolené kategorie, `lze_omezit`) |
| `GET /api/osoby/{id}` | správce osob | detail osoby, účet (heslo, pozvánka, poslední přihlášení), historie |
| `POST /api/osoby` | správce osob | nová osoba |
| `POST /api/osoby/{id}` | správce osob | změna údajů (jen poslané), člen, aktivní |
| `POST /api/osoby/{id}/opravneni` | správce osob | `{opravneni_id, kategorie_id, ma}` – oprávnění pro kategorii přidat / odebrat (s poslední kategorií zmizí oprávnění); nepovolená kategorie = 400 |
| `POST /api/osoby/{id}/omezeni` | správce osob | `{opravneni_id, omezene}` – omezený instruktor (jen u oprávnění, které osoba má) |
| `POST /api/ucty`, `POST /api/ucty/{id}`, `…/pozvanka` | správce osob (práva jen admin) | účet: založit, povolit / zablokovat, práva, odkaz pro heslo |
| `GET /api/ja` | přihlášený | práva už včetně „admin = vše“ (`admin`, `smi_odblokovat`, `spravuje_osoby`) |

Chyby z databáze (neplatný e-mail, telefon, číslo člena, duplicitní e-mail…) se vrátí jako
čitelná hláška.

## 5. Obrazovky (mobil)
- **Seznam** (pod hlavičkou a menu): pole hledání, segmenty filtru, karta s řádky osob
  (příjmení jméno, telefon vpravo; pod tím štítky). Ťuknutí otevře detail.
- **Detail** (vlastní horní lišta ← jméno, vpravo stav účtu): bloky jako detail letu – pole
  ve dvou sloupcích (popisek nad hodnotou, „›“ = upravit, úprava pod polem s Uložit / Zrušit);
  **zaškrtávátka** = dlaždice 44 px, popisek (a drobné vysvětlení) vlevo, políčko vpravo,
  zaškrtnuté modře a tučně, dvě vedle sebe; zaškrtnutí se uloží hned. Nedostupná volba
  (právo jen pro admina) je zašedlá. U admina jsou ostatní práva zaškrtnutá a zašedlá
  („má jako admin“); uložená hodnota platí, až mu admin odebere.
- **Nová osoba**: formulář a Uložit → otevře detail nové osoby.

## 6. Testy
Server: práva (bez práva 403, správce smí osoby, ne práva; admin vše; sám sobě), nová
osoba, úpravy a chyby z databáze, převod telefonu, oprávnění, historie. Klikací: záložka
jen pro správce, hledání, úprava telefonu, oprávnění, nová osoba, neaktivní.

## 7. Odkaz pro heslo e-mailem (hotovo 9. 10. 2026)
Tlačítko **Odkaz e-mailem** v bloku Účet a přihlášení – jen admin, ručně, s potvrzením adresy;
návrh a pravidla v `modul-email.md`. „Odkaz pro heslo“ (zkopírovat a předat) zůstává.
