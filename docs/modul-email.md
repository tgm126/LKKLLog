# Modul: e-mail (NÁVRH k odsouhlasení)

Zadání 9. 10. 2026: aplikace posílá e-maily z **info@lkkl.cz**. Navazuje na
`modul-osoby.md` kap. 7 (odkaz pro heslo e-mailem) a na pravidlo „žádné e-maily členům
před spuštěním; pozvánky jen ruční akcí správce“.

## 1. Rozsah první verze
- **Jediný e-mail: odkaz pro nastavení hesla** (první přihlášení i zapomenuté heslo).
  Pošle ho **správce osob ručně u jedné osoby** – nic se neposílá automaticky (založení osoby,
  zapnutí účtu ani nic jiného e-mail nespustí).
- Dnešní **Odkaz pro heslo** (zkopírovat a předat) zůstává jako záloha.
- Později (každé samostatně, až po odsouhlasení): samoobslužné „zapomněl jsem heslo“ na
  přihlášení, hromadné pozvánky po představení aplikace klubu, upozornění.

## 2. Odesílání
- **SMTP přes schránku info@lkkl.cz** na serveru one12 (VPS Centrum; schránka existuje).
  Port 587 se STARTTLS a přihlášením; knihovna Pythonu `smtplib` – žádná nová závislost.
- Přístup v **proměnných prostředí** (ne v gitu, ne v databázi):
  `LKKL_SMTP_SERVER`, `LKKL_SMTP_PORT` (587), `LKKL_SMTP_UZIVATEL` (info@lkkl.cz),
  `LKKL_SMTP_HESLO`, `LKKL_EMAIL_OD` („AK Kladno Log <info@lkkl.cz>“).
  Bez nich (vývoj, testy) se nic neodešle – e-mail se jen vypíše do logu serveru.
- Odeslání v rámci požadavku (jeden e-mail, časový limit 10 s); chyba SMTP se vrátí jako
  hláška „E-mail se nepodařilo odeslat: …“ a zapíše se do záznamu (kap. 4).
- Text **jen prostý** (bez HTML) – nejlépe doručitelný, nic k údržbě.

## 3. Pojistka: režim odesílání
Nový sloupec v **`lkkl.nastaveni`** (jediný řádek, db/034) a obrazovka Správa → Nastavení:

```sql
ALTER TABLE lkkl.nastaveni
    ADD COLUMN email_rezim text NOT NULL DEFAULT 'povolene'
        CHECK (email_rezim IN ('vypnuto', 'povolene', 'vsem')),
    ADD COLUMN email_povolene text[] NOT NULL DEFAULT '{}';
        -- adresy nebo domény (@lkkl.cz), jimž se smí posílat v režimu 'povolene'
```
- **vypnuto** – nic se neposílá (tlačítko řekne proč);
- **povolene** (výchozí) – jen na adresy ze seznamu (pro zkoušení vaše adresy);
- **vsem** – každé osobě s e-mailem (až po spuštění aplikace).

## 4. Záznam odeslaných e-mailů
Provozní tabulka – kdo, komu, kdy, s jakým výsledkem („nepřišlo mi to“ se dá dohledat).
**Obsah se neukládá** – odkaz pro heslo je tajný (kdo ho má, nastaví heslo).

```sql
CREATE TABLE lkkl.email (
    id        bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kdy       timestamptz NOT NULL DEFAULT now(),
    druh      text        NOT NULL CHECK (druh IN ('ODKAZ_HESLO')),
    osoba_id  bigint      NOT NULL REFERENCES lkkl.lov_osoba,   -- komu
    adresa    text        NOT NULL,                             -- na jakou adresu (stav v tu chvíli)
    odeslal_id bigint     NOT NULL REFERENCES lkkl.lov_osoba,   -- kdo
    vysledek  text        NOT NULL CHECK (vysledek IN ('ODESLANO', 'CHYBA', 'NEPOVOLENO')),
    chyba     text,                                             -- text chyby SMTP / důvod
    CHECK ((vysledek = 'ODESLANO') = (chyba IS NULL))
);
```
- `ucet.pozvanka_odeslana` zůstává (čas posledního vydání odkazu – zkopírovaného
  i odeslaného); v detailu osoby se ukáže „odkaz odeslán e-mailem 9. 10. 12:30“ z tabulky.
- **Omezení:** nejvýš 1 e-mail téže osobě za 5 minut (dvojklik, opakované mačkání).

## 5. Obrazovka (detail osoby, blok Účet a přihlášení)
- Vedle **Odkaz pro heslo** tlačítko **Poslat odkaz e-mailem**. Klik → potvrzení „Poslat
  odkaz pro nastavení hesla na jan.novak@…?“ → odeslat → oznámení „Odkaz odeslán“ nebo chyba.
- Nedostupné (zašedlé s vysvětlením): osoba bez e-mailu, účet vypnutý, režim *vypnuto*,
  adresa mimo povolené.
- Správa → **Nastavení**: blok **E-mail** – režim (vypnuto / povolené / všem) a seznam
  povolených adres.

## 6. Text e-mailu
Předmět: **AK Kladno Log – nastavení hesla**

> Dobrý den, {jméno},
> správce vám v aplikaci AK Kladno Log (evidence letů aeroklubu Kladno) připravil přístup.
> Heslo si nastavíte tímto odkazem – platí 3 dny a jen jednou:
> {odkaz}
> Přihlašovací jméno je tato e-mailová adresa. Pokud jste o přístup nežádali, e-mail
> ignorujte. Na tuto zprávu neodpovídejte – s dotazy se obraťte na {správce, e-mail}.

## 7. Práva a bezpečnost
- Poslat smí **správce osob** (a admin), ne v relaci jen ke čtení; server to hlídá.
- Odkaz platí 3 dny a po nastavení hesla přestane platit (stávající pravidlo).
- Doručitelnost: zkontrolovat v DNS domény lkkl.cz záznamy **SPF a DKIM** (VPS Centrum),
  jinak pošta skončí ve spamu; první e-maily jen na vaše adresy (Gmail i jiná schránka)
  a kontrola hlaviček.

## 8. Testy
Server (odesílání nahrazené zkušební schránkou v paměti): režimy, povolené adresy, záznam
a jeho výsledek, chyba SMTP, omezení 1 za 5 minut, práva (403, jen ke čtení), odkaz
v e-mailu funguje. Klikací: tlačítko, potvrzení, oznámení, zašedlé stavy, nastavení režimu.

## 9. K rozhodnutí
1. Rozsah – jen odkaz pro heslo ručně správcem (doporučuji), nebo hned i samoobslužné
   „zapomněl jsem heslo“ na přihlášení?
2. Režim odesílání v `nastaveni` s výchozím **povolené** a seznamem adres – souhlas?
3. Tabulka záznamu `email` bez obsahu – souhlas?
4. Text e-mailu (kap. 6) a koho uvést pro dotazy (adresa pro odpověď, `Reply-To`)?

## 10. Od vás
- **Heslo schránky info@lkkl.cz** zadáte sami do proměnných prostředí aplikace ve VPS
  Centru (do chatu ho nepište); název serveru SMTP ověřím ve VPS Centru.
- Adresy pro zkoušení (povolené v režimu *povolene*).
