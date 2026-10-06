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
  await expect(page.locator(".let.vzduch", { hasText: "OK-3819" })).toBeVisible();
  await oznameni.getByRole("button", { name: "ZPĚT" }).click();
  await expect(planovany).toBeVisible();
  await expect(oznameni).toBeHidden();

  const mfv = page.locator(".let.problem", { hasText: "OK-MFV" });
  await mfv.getByRole("button", { name: /T&G/ }).click();
  await expect(oznameni).toContainText("OK-MFV T&G");
  await expect(mfv.getByRole("button", { name: /T&G/ })).toHaveText("T&G 2");
  await mfv.getByRole("button", { name: "Přistál" }).click();
  await expect(page.locator(".let.ukoncen", { hasText: "OK-MFV" })).toContainText("3 přistání");
});

test("vlek ve vzduchu jako dvojice, detail ťuknutím na polovinu", async ({ page }) => {
  const par = page.locator(".let.naplanovan", { hasText: "OK-6722" });
  await par.getByRole("button", { name: "Vzlet" }).click();
  const veVzduchu = page.locator(".let.vzduch", { hasText: "OK-6722" });
  await expect(veVzduchu.locator(".let-par")).toHaveCount(2);
  await expect(veVzduchu).toContainText("Z 526 · vlečná");
  await expect(veVzduchu).not.toContainText("vleče");

  // Ťuknutí na polovinu vlečné otevře její detail.
  await veVzduchu.locator(".let-par", { hasText: "OK-CRA" }).getByText("Adam Admin").click();
  await expect(page.getByRole("heading", { name: /OK-CRA/ })).toBeVisible();
  await expect(page.getByRole("button", { name: /Vleče/ })).toContainText("OK-6722");
  await page.getByRole("button", { name: "Přistál" }).click();
  await page.getByRole("button", { name: "Zpět", exact: true }).click();

  // Vlečná přistála – kluzák zůstal ve vzduchu sám; vlečná mezi ukončenými se štítkem „vlek“.
  await expect(page.locator(".let.vzduch", { hasText: "OK-6722" }).locator(".let-par")).toHaveCount(1);
  await expect(page.locator(".let.ukoncen", { hasText: "OK-CRA" }).first()).toBeVisible();
  await page.locator(".let.vzduch", { hasText: "OK-6722" }).getByRole("button", { name: "Přistál" }).click();
  // vlečná má na místě účelu štítek „vlek“
  await expect(page.locator(".let.ukoncen .stitek", { hasText: /^vlek$/ })).toHaveCount(1);
});

test("osoba ve vzduchu nemůže vzlétnout jinde", async ({ page }) => {
  // Petr Pilot letí na OK-2817 – jako PIC dalšího letu ho server při vzletu odmítne.
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await page.getByRole("button", { name: "Všichni…" }).click();
  await page.getByRole("button", { name: "Petr Pilot" }).click();
  await page.getByRole("button", { name: "Dál" }).click();
  // (výchozí způsob vzletu je podle posledního dnešního – po předchozím testu aerovlek)
  await page.getByRole("button", { name: "Naviják" }).click();
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
  await expect(ucely).toHaveText(["Normální", "Výcvik sólo"]);
  const dal = page.getByRole("button", { name: "Dál" });
  await expect(dal).toBeDisabled();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await expect(page.getByRole("button", { name: "Já (Adam Admin)" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await dal.click();

  await expect(page.getByText("3 / 3 · Let")).toBeVisible();
  // Výchozí způsob vzletu = jak se dnes naposledy vzlétalo s kluzákem (předchozí test: aerovlek).
  await expect(page.getByRole("button", { name: "Aerovlek" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Naviják" }).click();
  // Platí předvyplněný PIC – vybraná volba modře jako ostatní volby.
  const plati = page.locator(".blok", { hasText: "Platí" });
  await expect(plati.getByRole("button", { name: "Adam Admin" })).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("button", { name: "Vzlet teď" }).click();

  await expect(page.getByRole("status")).toContainText(/OK-6722 vzlet/);
  await expect(page.locator(".let.vzduch", { hasText: "OK-6722" })).toContainText("Adam Admin");
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
  await page
    .locator(".blok", { hasText: "Instruktor (PIC)" })
    .getByRole("button", { name: "Já (Adam Admin)" })
    .click();
  const zak = page.locator(".blok", { hasText: "Žák" });
  await zak.getByRole("button", { name: "Všichni…" }).click();
  await zak.getByRole("button", { name: "Nela Nová" }).click();
  await page.getByRole("button", { name: "Dál" }).click();

  const uloha = page.locator(".blok", { hasText: "Úloha" });
  await expect(uloha.locator(".navrhy").first().getByRole("button")).toHaveText([
    /^IU/,
    /^IA/,
    /^II/,
  ]);
  await expect(page.getByRole("button", { name: "Naplánovat" })).toBeDisabled(); // úloha povinná
  await uloha.getByRole("button", { name: /^IU –/ }).click();
  const ulohyIU = uloha.locator(".navrhy").nth(1).getByRole("button");
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
