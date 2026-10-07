---
name: snimky-mobil
description: Vizuální kontrola obrazovek LKKL Log na telefonu – spuštění serveru nad e2e daty, snímky Playwrightem (Pixel 7, světlý i tmavý režim), měření rozměrů prvků, úklid. Použij po změně vzhledu (pásky, menu, dlaždice, štítky) nebo když uživatel chce vidět, jak obrazovka vypadá (jen v projektu LKKL Log).
---

# Snímky obrazovek na telefonu

Klikací testy (`npm run e2e`) ověří chování, ne vzhled. Po změně vzhledu obrazovku vyfoť a
prohlédni (Read na PNG), ve **světlém i tmavém** režimu.

## 1. Server nad testovacími daty (port 8001)
Frontend musí být sestavený (`npm run e2e` nebo `npm run build` ve `frontend/`).
```bash
cd /c/GIT/LKKLLog/backend
export LKKL_DATABAZE=postgresql://lkkllog:lkkllog@127.0.0.1:5432/lkkllog_e2e LKKL_ADRESA=http://localhost:8001
uv run python -m tests.e2e_priprava            # čerstvá testovací data (admin, Nela, flotila)
(uv run uvicorn app.main:app --port 8001 > /tmp/uv8001.log 2>&1 &) ; sleep 4
curl -s localhost:8001/api/health
```
Testovací data jdou upravit přímo v `lkkllog_e2e` (`docker exec lkkllog-dev-db-1 psql -U lkkllog -d lkkllog_e2e …`),
např. kvůli dlouhému popisu místa. Data uživatele (`lkkllog`) na snímky nepoužívat.

## 2. Dočasný skript `frontend/foto-tmp.mjs`
Musí být ve `frontend/` (kvůli `@playwright/test`), po použití smazat.
```js
import { chromium, devices } from "@playwright/test";
const ven = process.argv[2];
const b = await chromium.launch();
for (const schema of ["light", "dark"]) {
  const k = await b.newContext({ ...devices["Pixel 7"], colorScheme: schema });   // šířku jde přepsat viewportem (360 = nejužší Android)
  const p = await k.newPage();
  await p.goto("http://localhost:8001/prihlaseni");
  await p.getByLabel("E-mail").fill("admin@example.cz");
  await p.getByLabel("Heslo", { exact: true }).fill(/* HESLO_ADMINA z backend/tests/e2e_priprava.py */);
  await p.getByRole("button", { name: "Přihlásit" }).click();
  // … navigace; PŘED snímkem počkat na data, jinak bude stránka prázdná:
  await p.locator(".let").first().waitFor();
  await p.screenshot({ path: `${ven}/nazev-${schema}.png` });                    // clip: {x,y,width,height} pro výřez
  await k.close();
}
await b.close();
```
Spuštění: `node foto-tmp.mjs "<scratchpad>"`. Snímky do scratchpadu, ne do repozitáře.
Víc snímků vedle sebe: Pillow (`uv run --with pillow python -c …`), pak jeden Read.

## 3. Měření místo odhadu
Když jde o „vejde se / jsou stejně vysoké“, změř:
```js
console.log(await p.evaluate(() => [...document.querySelectorAll(".dlazdice")]
  .map((d) => Math.round(d.getBoundingClientRect().height)).join(" ")));
```
(šířky sloupců mřížky: `getComputedStyle(el).gridTemplateColumns`).

## 4. Úklid (vždy)
```powershell
Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -Confirm:$false }
```
a `rm frontend/foto-tmp.mjs`.

Makety (`docs/navrhy/*.html`) jde otevřít v panelu prohlížeče (`mcp__Claude_Browser__navigate`
na `file:///C:/GIT/LKKLLog/docs/navrhy/…`) nebo vyfotit stejným skriptem (`p.goto("file:///…")`,
`fullPage: true`).
