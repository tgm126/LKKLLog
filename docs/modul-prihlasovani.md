# Modul: účty a přihlašování

> **Schváleno 5. 10. 2026.** Změny chování nejdřív sem, pak do kódu.

Server: Python + FastAPI, dotazy přímo v SQL nad tabulkami `lkkl.ucet`, `lkkl.relace`
a pohledem `lkkl.v_ucet` (skript `db/005_ucet.sql`). V tomto kroku **bez obrazovek** –
rozhraní (API) ověří automatické testy; přihlašovací obrazovka přijde po vizuálním systému.

## 1. Rozsah

**Ano:** přihlášení e-mailem a heslem, odhlášení, „kdo jsem“, nastavení hesla odkazem
(pozvánka i zapomenuté heslo), aktivace osoby adminem, „přihlásit se jako“, přehled
a odhlášení zařízení, ochrana proti hádání hesla.

**Ne (později):** odesílání e-mailů a s ním samoobslužné „zapomenuté heslo“ (ve fázi 1 se
e-maily neposílají – odkaz pro nastavení hesla dostane admin a předá ho osobě sám), passkey,
auditní log (zatím neexistuje tabulka – kde má modul zapisovat, je v textu označeno *audit*).

**Práva:** `admin` (smí všechno), `spravuje_osoby` (správa osob, docs/modul-osoby.md) a `smi_odblokovat` (smí odblokovat účet zablokovaný po
neúspěšných pokusech; skript `db/006_odblokovani.sql`).

## 2. Pojmy

- **Účet** – řádek v `ucet`; existence = osoba aktivovaná v aplikaci.
- **Relace** – jedno přihlášené zařízení (řádek v `relace`).
- **Klíč relace** – náhodných 32 bajtů v cookie; v databázi jen jeho otisk SHA-256.
- **Odkaz pro nastavení hesla** – jednorázový podepsaný odkaz (viz kap. 4.4).

## 3. Rozhraní (API)

Vše pod `/api`, data JSON. Chyby: 400 neplatná data, 401 nepřihlášen, 403 chybí právo,
404 neexistuje, 429 dočasně zablokováno.

| Metoda a adresa | Kdo | Co dělá |
|---|---|---|
| `POST /api/prihlaseni` | kdokoli | `{email, heslo, jen_cteni}` → založí relaci (jen ke čtení: sdílený počítač, 4.2), nastaví cookie, vrátí „kdo jsem“ |
| `POST /api/odhlaseni` | přihlášený | ukončí aktuální relaci, smaže cookie |
| `GET /api/ja` | přihlášený | jméno, e-mail, práva (`admin`), případně „přihlášen jako“ (kdo je skutečný admin) |
| `GET /api/zarizeni` | přihlášený | moje relace: zařízení, poslední aktivita, které je aktuální |
| `POST /api/zarizeni/odhlasit-ostatni` | přihlášený | ukončí všechny moje relace kromě aktuální |
| `GET /api/heslo/odkaz?klic=…` | kdokoli | ověří odkaz → jméno osoby, nebo „odkaz neplatí“ |
| `POST /api/heslo/nastavit` | kdokoli s odkazem | `{klic, heslo}` → uloží heslo, zneplatní odkaz, rovnou přihlásí |
| `POST /api/heslo/zmenit` | přihlášený | `{stare, nove}` → změní heslo, odhlásí ostatní zařízení |
| `POST /api/ucty` | admin | `{osoba_id, admin, smi_odblokovat}` → aktivuje osobu (založí účet) |
| `POST /api/ucty/{osoba_id}` | admin | změní `aktivni`, `admin`, `smi_odblokovat`; zablokování ukončí všechny relace osoby |
| `POST /api/ucty/{osoba_id}/pozvanka` | admin | vrátí odkaz pro nastavení hesla (admin ho předá osobě), zapíše `pozvanka_odeslana` |
| `GET /api/ucty` | admin | přehled účtů (z `v_ucet`) |
| `GET /api/ucty/zablokovane` | admin, `smi_odblokovat` | účty zablokované po neúspěšných pokusech (jen jméno a do kdy) |
| `POST /api/ucty/{osoba_id}/odblokovat` | admin, `smi_odblokovat` | zruší zablokování a vynuluje pokusy |
| `POST /api/prihlasit-jako/{osoba_id}` | admin | aktuální relace začne jednat za jinou osobu |
| `POST /api/prihlasit-jako/konec` | „přihlášen jako“ | návrat k vlastnímu účtu |

## 4. Chování

### 4.1 Přihlášení
1. E-mail se porovná bez ohledu na velikost písmen (`lower(email)`).
2. Přihlásit se smí jen účet z `v_ucet` se `smi_se_prihlasit` a nastaveným heslem.
3. Při chybě vždy stejná odpověď **„Nesprávný e-mail nebo heslo“** – nesmí prozradit, zda
   e-mail existuje. I pro neexistující e-mail se ověřuje (fiktivní) otisk, aby odpověď
   trvala stejně dlouho.
4. **Ochrana proti hádání:** po **5** neúspěšných pokusech se účet zablokuje na **15 minut**
   (`zablokovano_do`, odpověď 429). Úspěšné přihlášení počítadlo vynuluje. Dřív ho může
   odblokovat admin nebo osoba s právem `smi_odblokovat`. Zablokování brání jen novému
   přihlášení – už přihlášená zařízení fungují dál (útočník tak nemůže vlastníka „vyhodit“).
   Odpověď 429 prozradí, že účet existuje; je to vědomý kompromis (jinak by člověk nevěděl,
   že má požádat o odblokování).
5. Úspěch: nová relace (`plati_do` = teď + 30 dní), `posledni_prihlaseni`, cookie. *audit*

### 4.2 Relace a cookie
- Cookie `lkkl_relace`: `HttpOnly`, `Secure`, `SameSite=Lax`, cesta `/`, platnost 30 dní.
- Každý požadavek: otisk klíče → řádek v `relace` s `plati_do > now()` a účtem, který se
  smí přihlásit. Jinak 401 (a relace se smaže).
- **Prodlužování:** `posledni_aktivita` a `plati_do` (+30 dní) se zapíší nejvýš jednou za
  hodinu, aby se do databáze nezapisovalo při každém kliknutí.
- Prošlé relace maže úklid (příkaz pro cron, později na serveru).
- **Jen ke čtení** (`relace.jen_cteni`, db/030; docs/modul-desktop.md 6.1): zaškrtávátko
  u přihlášení pro sdílený počítač. V takové relaci závislost `prihlaseny` odmítne každý
  požadavek kromě čtení (403), práva se neuplatní a `GET /api/ja` vrací `jen_cteni`. Odhlásit
  se jde vždy; k zápisu je potřeba se přihlásit znovu bez zaškrtnutí.

### 4.3 Ochrana proti podvrženým požadavkům (CSRF)
Rozhraní přijímá jen JSON. Každý požadavek, který něco mění (POST), musí mít hlavičku
`Origin` z povolených adres (proměnná `LKKL_POVOLENE_ADRESY`); jinak 403. Spolu s `SameSite=Lax` to brání tomu,
aby cizí stránka poslala požadavek s cookie přihlášeného uživatele.

### 4.4 Odkaz pro nastavení hesla
- Odkaz `…/heslo?klic=…` je **podepsaný tajným klíčem serveru** a obsahuje osobu a čas
  vydání; platí **3 dny**. Nic se kvůli němu neukládá do databáze.
- Je **jednorázový**: podpis zahrnuje `heslo_zmeneno`, takže po nastavení hesla přestane
  platit (i všechny starší odkazy).
- Pozvánka i (později) zapomenuté heslo používají stejný odkaz. Ve fázi 1 ho admin získá
  z `POST /api/ucty/{osoba_id}/pozvanka`, první heslo admina příkazem
  `uv run python -m app.prikazy odkaz <e-mail>`.

### 4.5 Heslo
- Délka **10 až 128 znaků**, žádná další pravidla (velká písmena, číslice) – delší heslo je
  bezpečnější než složité. Otisk **argon2id**.
- Nastavení i změna hesla zapíše `heslo_zmeneno`, vynuluje pokusy a **odhlásí ostatní
  zařízení**. *audit*

### 4.6 Aktivace a blokování (admin)
- Aktivace = založení účtu (heslo prázdné). Databáze pohlídá, že osoba má e-mail.
- Zablokování (`aktivni = false`) ukončí všechny relace osoby. Odblokování je vrátí do hry
  (heslo zůstává). *audit*
- Admin nemůže zablokovat ani odebrat `admin` sám sobě (aby nezůstal systém bez admina).

### 4.7 Přihlásit se jako
- Jen admin; za **jiného admina** se přihlásit nejde.
- Aktuální relace dostane `osoba_id` = cílová osoba, `puvodni_osoba_id` = admin. Relace se
  chová přesně jako přihlášení té osoby (práva té osoby, ne admina).
- `GET /api/ja` vrací i skutečného admina (obrazovka ukáže pruh „Jste přihlášen jako …“).
- `konec` vrátí relaci adminovi. *audit* (zapisuje se skutečný admin).

### 4.8 Audit (kdo jedná)
Každý požadavek nastaví databázi kontext auditu (`db.s_kontextem`, proměnné relace
`lkkl.zdroj`, `lkkl.osoba_id`, `lkkl.puvodni_osoba_id`), který čte trigger auditu
(`db/012_audit.sql`). Bez přihlášení jde o „aplikaci“ (např. zablokování po neúspěšných
pokusech); po ověření relace se doplní přihlášená osoba a při „přihlásit se jako“ i skutečný
admin; při nastavení hesla odkazem osoba z odkazu. Po požadavku se kontext zruší (spojení se
vrací do poolu). Úspěšné přihlášení do auditu nic nepíše (poslední přihlášení a počet pokusů
se nesledují, prošlé zablokování zůstane).

## 5. Obrazovky (schváleno 6. 10. 2026)

Maketa `docs/navrhy/prihlaseni-mobil.html`; kód `frontend/src/stranky/Prihlaseni.tsx`,
`NastaveniHesla.tsx`, klikací testy `frontend/e2e/prihlaseni.spec.ts`.

1. **Přihlášení:** e-mail, heslo (Ukázat), Přihlásit; formulář nahoře (klávesnice zakryje
   spodek displeje). Při chybě hláška nad tlačítkem, heslo se smaže, kurzor do hesla.
   Nepřihlášený jde na přihlášení a po něm zpět, kam mířil.
2. **Nastavení hesla** (`/heslo?klic=…`): jméno osoby, heslo jen jednou s Ukázat, průběžná
   nápověda délky, tlačítko až od 10 znaků; po uložení přihlášen. Neplatný odkaz = hláška
   a „Na přihlášení“. `GET /api/heslo/odkaz` vrací i e-mail (správce hesel uloží heslo
   ke správnému účtu).
3. Písmo textových polí 16 px (token `--pismo-pole`, VÝJIMKA kvůli přibližování na iPhonu).
4. **Pruh** nahoře na všech obrazovkách podle fáze provozu (tabulka `provoz`: TESTOVACÍ /
   PILOTNÍ PROVOZ, v ostrém bez pruhu; lokálně „VÝVOJ“); **verze** dole na přihlášení.
   Obojí z `GET /api/aplikace`.
5. Po přihlášení hlavička s menu a nabídkou uživatele (jméno, režim zobrazení, odhlásit);
   „přihlášen jako“ = pruh s návratem na vlastní účet.
6. Změna hesla a přehled zařízení v nabídce uživatele později (samostatný krok).

## 6. Struktura kódu

```
backend/
  pyproject.toml          závislosti přes uv (fastapi, uvicorn, psycopg, argon2-cffi, pytest…)
  app/
    main.py               aplikace FastAPI, připojení k databázi
    db.py                 pool spojení, pomocné funkce pro SQL
    bezpecnost.py         otisky hesel, klíče relací, podpis odkazů, kontrola Origin
    prihlasovani.py       adresy z kap. 3
  tests/                  testy proti lokální databázi (každý test v transakci, která se vrátí)
```

Testy pokryjí každé pravidlo z kap. 4: chybné heslo, neexistující e-mail, zablokování po
5 pokusech, prošlá a zneplatněná relace, prošlý a použitý odkaz, CSRF bez `Origin`,
přihlásit se jako (i zákaz za admina), zablokování ukončí relace.

## 6. Rozhodnutí ke schválení (5. 10. 2026)

1. E-maily se ve fázi 1 neposílají; odkaz pro nastavení hesla předává admin. Odesílání
   e-mailů bude samostatný modul před fází 2.
2. Zablokování po 5 pokusech na 15 minut, s možností dřívějšího odblokování (právo
   `smi_odblokovat`).
3. Heslo 10–128 znaků bez dalších pravidel.
