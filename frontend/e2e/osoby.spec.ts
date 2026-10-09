import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Správa osob (docs/modul-osoby.md): admin má všechna práva, Nela žádné.

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("osoby: hledání, úprava telefonu, oprávnění", async ({ page }) => {
  await page.getByRole("link", { name: "Osoby" }).click();
  await page.getByLabel("Hledat jméno, e-mail, telefon, číslo člena").fill("nova");
  const radky = page.locator(".radek-osoby");
  await expect(radky).toHaveCount(1);
  await expect(radky.first()).toContainText("Vlekař"); // oprávnění z přípravy dat
  await radky.first().click();
  await expect(page.getByRole("heading", { name: "Nová Nela" })).toBeVisible();

  // Telefon se uloží s předvolbou a zobrazí po trojicích.
  await page.getByRole("button", { name: /^Telefon/ }).click();
  await page.getByLabel("Telefon", { exact: true }).fill("602 123 456");
  await page.getByRole("button", { name: "Uložit" }).click();
  await expect(page.getByRole("button", { name: /Telefon\s*\+420 602 123 456/ })).toBeVisible();

  // Oprávnění po kategoriích (uloží se hned): FI(S) pro kluzák, pak omezený.
  const fi = page.getByRole("group", { name: "FI(S)" });
  await expect(fi.getByRole("button", { name: "omezený" })).toHaveCount(0);
  const kluzak = fi.getByRole("button", { name: "Kluzák", exact: true });
  await kluzak.click();
  await expect(kluzak).toHaveAttribute("aria-pressed", "true");
  const omezeny = fi.getByRole("button", { name: "omezený" });
  await omezeny.click();
  await expect(omezeny).toHaveAttribute("aria-pressed", "true");

  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  const nela = page.locator(".radek-osoby", { hasText: "Nová Nela" });
  await expect(nela).toContainText("+420 602 123 456");
  await expect(nela).toContainText("FI(S)");
});

test("osoby: nová osoba a vypnutí", async ({ page }) => {
  await page.getByRole("link", { name: "Osoby" }).click();
  await page.getByRole("button", { name: "+ Nová osoba" }).click();
  await expect(page.getByRole("heading", { name: "Nová osoba" })).toBeVisible();
  await page.getByLabel("Jméno", { exact: true }).fill("Karel");
  await page.getByLabel("Příjmení", { exact: true }).fill("Test");
  await page.getByLabel("Telefon", { exact: true }).fill("777 888 999");
  await page.getByRole("button", { name: "Uložit" }).click();
  await expect(page.getByRole("heading", { name: "Test Karel" })).toBeVisible();
  await expect(page.getByText("bez účtu", { exact: true })).toBeVisible();

  await page.getByRole("checkbox", { name: /^Aktivní/ }).click();
  await expect(page.getByText("neaktivní", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  await expect(page.locator(".radek-osoby", { hasText: "Test Karel" })).toHaveCount(0);
  await page.getByRole("button", { name: /^Neaktivní/ }).click();
  await expect(page.locator(".radek-osoby", { hasText: "Test Karel" })).toHaveCount(1);
});

test("osoby: bez práva záložka chybí (přihlásit se jako)", async ({ page }) => {
  await page.getByRole("link", { name: "Osoby" }).click();
  await page.locator(".radek-osoby", { hasText: "Nová Nela" }).click();
  await page.getByRole("button", { name: "Přihlásit se jako" }).click();
  await expect(page.getByText("Přihlášen jako Nela Nová")).toBeVisible();
  await expect(page.getByRole("link", { name: "Osoby" })).toHaveCount(0);
  await page.getByRole("button", { name: "Zpět na svůj účet" }).click();
  await expect(page.getByRole("link", { name: "Osoby" })).toBeVisible();
});

test("osoby: admin má všechna práva zaškrtnutá a zašedlá", async ({ page }) => {
  await page.getByRole("link", { name: "Osoby" }).click();
  await page.getByLabel("Hledat jméno, e-mail, telefon, číslo člena").fill("admin");
  await page.locator(".radek-osoby").first().click();
  for (const pravo of [/^Spravuje osoby/, /^Spravuje letadla/, /^Smí odblokovat/]) {
    const z = page.getByRole("checkbox", { name: pravo });
    await expect(z).toHaveAttribute("aria-checked", "true");
    await expect(z).toBeDisabled();
  }
});

test("osoby: admin pošle odkaz pro heslo e-mailem (s potvrzením)", async ({ page }) => {
  // e2e server nemá SMTP – e-mail se jen vypíše do logu, odeslání projde (docs/modul-email.md)
  await page.getByRole("link", { name: "Osoby" }).click();
  await page.locator(".radek-osoby", { hasText: "Nová Nela" }).click();
  const poslat = page.getByRole("button", { name: "Odkaz e-mailem" });
  await poslat.click();
  const potvrzeni = page.getByRole("dialog", { name: "Poslat odkaz e-mailem?" });
  await expect(potvrzeni).toContainText("info@lkkl.cz");
  await potvrzeni.getByRole("button", { name: "Zpět" }).click();
  await expect(potvrzeni).toHaveCount(0);

  await poslat.click();
  await potvrzeni.getByRole("button", { name: "Poslat" }).click();
  await expect(page.getByRole("status")).toContainText("Odkaz odeslán na");
  await expect(page.locator(".info-uctu")).toContainText("odkaz e-mailem");
  // znovu hned nejde (nejvýš 1 za 5 minut)
  await poslat.click();
  await potvrzeni.getByRole("button", { name: "Poslat" }).click();
  await expect(page.getByRole("status")).toContainText("za 5 minut");
});
