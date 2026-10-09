# Modul: e-mail

Zadání 9. 10. 2026, odsouhlaseno 9. 10. 2026: aplikace posílá e-maily z **info@lkkl.cz**.
Navazuje na `modul-osoby.md` kap. 7 (odkaz pro heslo e-mailem) a na pravidlo „žádné e-maily
členům před spuštěním; pozvánky jen ruční akcí“.

## 1. Rozsah
- **Jediný e-mail: odkaz pro nastavení hesla** (první přihlášení i zapomenuté heslo).
  Pošle ho **jen admin, ručně u jedné osoby** (v aplikaci bude kolem 30 lidí) – nic se
  neposílá automaticky (založení osoby, zapnutí účtu ani nic jiného e-mail nespustí).
  Pojistka typu „režim odesílání“ není potřeba – každé odeslání je vědomé, s potvrzením adresy
  (rozhodnuto 9. 10. 2026).
- Dosavadní tlačítko **Odkaz pro heslo** (odkaz se zkopíruje a předá) zůstává jako záloha.
- Samoobslužné „zapomněl jsem heslo“ na přihlášení ani hromadné pozvánky nejsou.

## 2. Odesílání
- **SMTP přes schránku info@lkkl.cz** na serveru one12 (VPS Centrum; schránka existuje).
  Port 587 se STARTTLS a přihlášením; knihovna Pythonu `smtplib` – žádná nová závislost.
- Přístup v **proměnných prostředí** (ne v gitu, ne v databázi):
  `LKKL_SMTP_SERVER`, `LKKL_SMTP_PORT` (výchozí 587), `LKKL_SMTP_UZIVATEL` (info@lkkl.cz),
  `LKKL_SMTP_HESLO`, `LKKL_EMAIL_OD` (výchozí „AK Kladno Log <info@lkkl.cz>“),
  `LKKL_EMAIL_ODPOVED` (adresa pro dotazy a odpovědi – `Reply-To` a podpis e-mailu).
  Bez `LKKL_SMTP_SERVER` (vývoj, testy) se nic neodešle – e-mail se jen vypíše do logu serveru.
- Odeslání v rámci požadavku (časový limit 10 s); chyba SMTP se vrátí jako hláška „E-mail se
  nepodařilo odeslat: …“ a zapíše se do záznamu (kap. 3).
- Text **jen prostý** (bez HTML) – nejlépe doručitelný, nic k údržbě.

## 3. Záznam odeslaných e-mailů
Provozní tabulka – kdo, komu, kdy, s jakým výsledkem („nepřišlo mi to“ se dá dohledat).
**Obsah se neukládá** – odkaz pro heslo je tajný (kdo ho má, nastaví heslo).

```sql
CREATE TABLE lkkl.email (
    id         bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kdy        timestamptz NOT NULL DEFAULT now(),
    druh       text        NOT NULL CHECK (druh IN ('ODKAZ_HESLO')),
    osoba_id   bigint      NOT NULL REFERENCES lkkl.lov_osoba,  -- komu
    adresa     text        NOT NULL,                            -- adresa v tu chvíli
    odeslal_id bigint      NOT NULL REFERENCES lkkl.lov_osoba,  -- kdo
    chyba      text,                                            -- prázdná = odesláno
    CHECK (chyba IS NULL OR btrim(chyba) <> '')
);
```
- `ucet.pozvanka_odeslana` zůstává (čas posledního vydání odkazu – zkopírovaného
  i odeslaného); v detailu osoby se ukáže poslední e-mail („odkaz e-mailem 9. 10. 12:30“,
  případně „e-mail se nepodařilo odeslat“).
- **Omezení:** téže osobě nejvýš 1 odeslaný e-mail za 5 minut (dvojklik, opakované mačkání).

## 4. Obrazovka (detail osoby na telefonu, blok Účet a přihlášení)
Správa osob zůstává **jen na telefonu** (a v úzkém okně) – rozhodnuto 9. 10. 2026.
- Vedle **Odkaz pro heslo** tlačítko **Odkaz e-mailem** – jen pro admina. Klik →
  potvrzení „Poslat odkaz pro nastavení hesla na jan.novak@…?“ → odeslat → oznámení
  „Odkaz odeslán na …“ nebo chyba.
- Zašedlé (jako Odkaz pro heslo), když osoba nemá účet nebo se nesmí přihlásit.

## 5. Text e-mailu
Předmět: **AK Kladno Log – nastavení hesla**

> Dobrý den, {jméno},
>
> v aplikaci AK Kladno Log (evidence letů aeroklubu Kladno) máte připravený přístup.
> Heslo si nastavíte tímto odkazem – platí 3 dny, po nastavení hesla už ne:
> {odkaz}
>
> Přihlašovací jméno je tato e-mailová adresa. Pokud jste o přístup nežádali, e-mail
> ignorujte. S dotazy se obraťte na {LKKL_EMAIL_ODPOVED} (stačí odpovědět na tento e-mail).
>
> AK Kladno

## 6. Práva a bezpečnost
- Poslat smí **jen admin**, ne v relaci jen ke čtení; server to hlídá.
- Odkaz platí 3 dny a po nastavení hesla přestane platit (stávající pravidlo).
- Doručitelnost: zkontrolovat v DNS domény lkkl.cz záznamy **SPF a DKIM** (VPS Centrum),
  jinak pošta skončí ve spamu; první e-maily jen na adresy uživatele (Gmail i jiná
  schránka) a kontrola hlaviček.

## 7. Testy
Server (odesílání nahrazené zkušební schránkou v paměti): odeslání a text (odkaz v e-mailu
funguje), záznam, chyba SMTP, omezení 1 za 5 minut, práva (jen admin, ne jen ke čtení),
osoba bez účtu. Klikací: tlačítko jen u admina, potvrzení, oznámení.

## 8. Nasazení
Uživatel zadá ve VPS Centru proměnné prostředí aplikace (kap. 2) – heslo schránky jen tam.
