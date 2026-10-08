import { expect, test } from "@playwright/test";

import { prihlasit, prihlasitJenCteni, pripravitData } from "./pomocne";

// Správa systému z nabídky uživatele – jen admin (docs/modul-sprava.md); mobil.

test.beforeAll(() => pripravitData());
test.afterAll(() => pripravitData()); // smazání dne mění lety pro další testy

test("správa: smazat lety dne v kalendáři s potvrzením", async ({ page }) => {
  await prihlasit(page);
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: "Smazat lety dne…" }).click();

  // Dnešek má lety: tučně s počtem, ostatní dny nejdou vybrat
  const kalendar = page.getByRole("region", { name: "Kalendář letů" });
  const den = kalendar.getByRole("button", { name: / – 8 letů$/ });
  await expect(den).toBeEnabled();
  await expect(kalendar.locator(".kalendar-den:disabled").first()).toBeVisible();

  // Zpět v potvrzení nic nesmaže
  await den.click();
  const potvrzeni = page.getByRole("dialog");
  await expect(potvrzeni).toContainText("Smaže se 8 letů");
  await potvrzeni.getByRole("button", { name: "Zpět" }).click();
  await expect(den).toBeEnabled();

  await den.click();
  await potvrzeni.getByRole("button", { name: "Smazat 8 letů" }).click();
  await expect(page.getByRole("status")).toContainText("Smazáno 8 letů");
  await expect(den).toHaveCount(0);

  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Ve vzduchu/ })).toHaveCount(0);
});

test("správa: nastavení testovacího provozu", async ({ page }) => {
  await prihlasit(page);
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: "Nastavení" }).click();
  const test = page.getByRole("checkbox", { name: /Testovací provoz/ });
  await expect(test).toBeChecked();
  await test.click();
  await expect(test).not.toBeChecked();
  await page.reload();
  await expect(test).not.toBeChecked();
  await test.click(); // zpět do výchozího stavu
  await expect(test).toBeChecked();
});

test("správa: jen ke čtení bez položek správy", async ({ page }) => {
  await prihlasitJenCteni(page);
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await expect(page.getByRole("button", { name: "Odhlásit" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Smazat lety dne…" })).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Nastavení" })).toHaveCount(0);
});
