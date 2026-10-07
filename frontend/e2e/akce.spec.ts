import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Akce z pásků a průvodce novým letem (docs/modul-lety.md); lety z e2e_priprava.py.

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("vzlet a Zpět, T&G a přistání z pásku", async ({ page }) => {
  const oznameni = page.getByRole("status");

  const planovany = page.locator(".let.naplanovan", { hasText: "OK-3819" });
  await planovany.getByRole("button", { name: "Vzlet" }).click();
  await expect(oznameni).toContainText(/OK-3819 vzlet \d\d:\d\d:\d\d/);
  await expect(page.locator(".let:is(.vzduch, .problem)", { hasText: "OK-3819" })).toBeVisible();
  await oznameni.getByRole("button", { name: "ZPĚT" }).click();
  await expect(planovany).toBeVisible();
  await expect(oznameni).toBeHidden();

  const mfv = page.locator(".let.problem", { hasText: "OK-MFV" });
  await mfv.getByRole("button", { name: /T&G/ }).click();
  await expect(oznameni).toContainText("OK-MFV T&G");
  await expect(mfv.getByRole("button", { name: /T&G/ })).toHaveText("T&G 2");
  await mfv.getByRole("button", { name: "Přistál" }).click();
  await expect(
    page.locator(".denik-radek.ukoncen", { hasText: "OK-MFV" }).locator(".denik-pristani"),
  ).toHaveText("3");
});

test("vlek ve vzduchu jako dvojice, detail ťuknutím na polovinu", async ({ page }) => {
  const par = page.locator(".let.naplanovan", { hasText: "OK-6722" });
  await par.getByRole("button", { name: "Vzlet" }).click();
  const veVzduchu = page.locator(".let:is(.vzduch, .problem)", { hasText: "OK-6722" });
  await expect(veVzduchu.locator(".let-par")).toHaveCount(2);
  await expect(veVzduchu).toContainText("Z 526 · vlečná");
  await expect(veVzduchu).not.toContainText("vleče");
  // Vlečná nemá T&G (při vleku se nedělá).
  await expect(veVzduchu.getByRole("button", { name: /T&G/ })).toHaveCount(0);

  // Ťuknutí na polovinu vlečné otevře její detail.
  await veVzduchu.locator(".let-par", { hasText: "OK-CRA" }).getByText("Adam Admin").click();
  await expect(page.locator(".obrazovka .let-hlava")).toContainText("OK-CRA");
  await expect(page.getByRole("button", { name: /Vleče/ })).toContainText("OK-6722");
  // Let kratší než minuta: dialog – počítat (1 minuta), nebo zrušit.
  await page.getByRole("button", { name: "Přistál" }).click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toContainText("let kratší než minuta");
  await dialog.getByRole("button", { name: "Počítat let" }).click();
  await expect(page.getByText("Ukončený", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Zpět", exact: true }).click();

  // Vlečná přistála – kluzák zůstal ve vzduchu sám; vlečná v deníku s účelem „vlek“.
  const kluzak = page.locator(".let:is(.vzduch, .problem)", { hasText: "OK-6722" });
  await expect(kluzak.locator(".let-par")).toHaveCount(1);
  const vlek = page.locator(".denik-radek.ukoncen .seda", { hasText: /· vlek$/ });
  await expect(vlek).toHaveCount(1);
  // Kluzák po přetrženém laně: zrušit jako přerušený vzlet (vlečná zůstane ukončená).
  await kluzak.getByRole("button", { name: "Přistál" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "Zrušit – přerušený vzlet" }).click();
  await expect(page.getByRole("status")).toHaveText(/OK-6722 zrušen – přerušený vzlet/);
  await expect(vlek).toHaveCount(1);
});

test("osoba ve vzduchu nemůže vzlétnout jinde", async ({ page }) => {
  // Petr Pilot letí na OK-2817 – jako PIC dalšího letu ho server při vzletu odmítne.
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await page.getByRole("button", { name: "Hledat…" }).click();
  await page.getByLabel("Hledat osobu").fill("petr");
  await page.getByRole("button", { name: "Petr Pilot" }).click();
  await page.getByRole("button", { name: "Dál" }).click();
  // (výchozí způsob vzletu je podle posledního dnešního – po předchozím testu aerovlek)
  await page.getByRole("button", { name: "Naviják", exact: true }).click();
  await page.getByRole("button", { name: "Vzlet teď" }).click();
  await expect(page.getByRole("alert")).toHaveText(
    "Petr Pilot je v tu dobu na palubě jiného letu (OK-2817).",
  );

  // Naplánovat jde; VZLET z pásku pak ukáže stejnou hlášku v liště dole.
  await page.getByRole("button", { name: "Naplánovat" }).click();
  const planovany = page.locator(".let.naplanovan", { hasText: "Petr Pilot" });
  await planovany.getByRole("button", { name: "Vzlet" }).click();
  await expect(page.getByRole("status")).toHaveText(
    /Petr Pilot je v tu dobu na palubě jiného letu \(OK-2817\)\./,
  );
  await expect(page.getByRole("status")).toHaveCSS("color", "rgb(255, 255, 255)");
});

test("průvodce: VZLET TEĎ", async ({ page }) => {
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await expect(page.getByRole("heading", { name: "Nový let" })).toBeVisible();
  await page.getByRole("button", { name: /^OK-6722/ }).click();

  await expect(page.getByText("2 / 3 · Posádka")).toBeVisible();
  // Jednomístný kluzák: jen normální let a sólo (výcvik a přezkoušení mají na palubě dva).
  const ucely = page.locator(".blok", { hasText: "Účel" }).getByRole("button");
  await expect(ucely).toHaveText(["Normální", "Sólo"]);
  const dal = page.getByRole("button", { name: "Dál" });
  await expect(dal).toBeDisabled();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await expect(page.getByRole("button", { name: "Já (Adam Admin)" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await dal.click();

  await expect(page.getByText("3 / 3 · Let")).toBeVisible();
  // Rozpracovaný pásek nahoře ukazuje, co je vybrané; místo vzletu předvyplněné domovským.
  await expect(page.locator(".let.rozpracovany")).toContainText("Adam Admin");
  await expect(page.getByRole("button", { name: /Místo vzletu\s*LKKL Kladno/ })).toBeVisible();
  // Výchozí způsob vzletu = jak se dnes naposledy vzlétalo s kluzákem (předchozí test: aerovlek).
  await expect(page.getByRole("button", { name: "Aerovlek", exact: true })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByRole("button", { name: "Naviják", exact: true }).click();
  await expect(page.locator(".let.rozpracovany .stitky-pasku")).toContainText("naviják");
  // Platí předvyplněný PIC.
  await expect(page.getByRole("button", { name: /Platí\s*Adam Admin/ })).toBeVisible();
  await page.getByRole("button", { name: "Vzlet teď" }).click();

  await expect(page.getByRole("status")).toContainText(/OK-6722 vzlet/);
  await expect(page.locator(".let:is(.vzduch, .problem)", { hasText: "OK-6722" })).toContainText("Adam Admin");
});

test("průvodce: proběhlý let s časy prstem", async ({ page }) => {
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-CRA/ }).click();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await page.getByRole("button", { name: "Dál" }).click();
  await expect(page.getByText("3 / 3 · Let")).toBeVisible();
  await page.getByRole("button", { name: "Proběhlý let" }).click();

  await expect(page.getByText("Proběhlý let", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Včera" }).click();
  await page.getByRole("button", { name: "10", exact: true }).click();
  await page.getByRole("button", { name: "10:00" }).click();
  // Po vzletu se samo otevře přistání.
  await page.getByRole("button", { name: "10", exact: true }).click();
  await page.getByRole("button", { name: "10:45" }).click();
  await expect(page.getByText('Doba letu 45"')).toBeVisible();
  await page.getByRole("button", { name: "2", exact: true }).click(); // přistání celkem
  await page.getByRole("button", { name: "Uložit proběhlý let" }).click();

  await expect(page.getByRole("status")).toHaveText(/OK-CRA proběhlý let 10:00–10:45 uložen/);
});

test("průvodce: úloha ve dvou krocích – osnova, pak úloha", async ({ page }) => {
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await page.getByRole("button", { name: "Výcvik", exact: true }).click();
  // Za instruktora se rychle nabízí jen kdo má oprávnění instruktora kluzáků (FI(S)).
  const instruktor = page.locator(".blok", { hasText: "Instruktor (PIC)" });
  await expect(instruktor.getByRole("button")).toHaveText(["Já (Adam Admin)", "Hledat…"]);
  await instruktor.getByRole("button", { name: "Já (Adam Admin)" }).click();
  const zak = page.locator(".blok", { hasText: "Žák" });
  await zak.getByRole("button", { name: "Hledat…" }).click();
  await zak.getByRole("button", { name: "Nela Nová" }).click();
  await page.getByRole("button", { name: "Dál" }).click();

  const uloha = page.locator(".blok", { hasText: "Úloha" });
  await expect(uloha.locator(".cipy").getByRole("button")).toHaveText([
    /^IU/,
    /^IA/,
    /^II/,
  ]);
  await expect(page.getByRole("button", { name: "Naplánovat" })).toBeDisabled(); // úloha povinná
  await uloha.getByRole("button", { name: /^IU –/ }).click();
  const ulohyIU = uloha.locator(".seznam-voleb").getByRole("button");
  await expect(ulohyIU.first()).toHaveText("IU/1 Seznamovací let");
  await expect(ulohyIU.last()).toHaveText("IU/13 Traťový navigační let");
  await uloha.getByRole("button", { name: "IU/4 Navijákové vzlety, okruh a přistání" }).click();
  // Vybraná osnova a úloha zůstanou samy, ostatní se skryjí.
  await expect(uloha.getByRole("button")).toHaveText([
    /^IU –/,
    "IU/4 Navijákové vzlety, okruh a přistání",
  ]);
  await page.getByRole("button", { name: "Naplánovat" }).click();
  await expect(page.getByRole("status")).toHaveText(/OK-3819 naplánován/);
});
