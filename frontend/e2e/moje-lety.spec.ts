import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Moje lety na telefonu (docs/modul-moje-lety.md): jen lety, kde jsem v posádce; den jde
// vybrat, šipky po dnech s mými lety; detail a zpět na stejný den. Data z e2e_priprava.py
// (admin letí vlečnou OK-CRA, OK-CRA do Letňan a před třemi dny OK-2817).

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("moje lety: jen moje, předchozí den s lety, detail a zpět", async ({ page }) => {
  await page.getByRole("link", { name: "Moje lety" }).click();
  await expect(page.getByText(/ · dnes$/)).toBeVisible();
  const obsah = page.locator("main");
  // vlek celý (vlečná je moje, kluzák letí Nela), OK-CRA do Letňan; cizí lety ne
  await expect(obsah).toContainText("OK-6722");
  await expect(obsah).toContainText("OK-CRA");
  await expect(obsah).not.toContainText("OK-MFV");
  await expect(page.getByRole("button", { name: "Další den s mými lety" })).toBeDisabled();

  await page.getByRole("button", { name: "Předchozí den s mými lety" }).click();
  await expect(page).toHaveURL(/\/moje-lety\?den=\d{4}-\d{2}-\d{2}$/);
  await expect(page.getByRole("heading", { name: /Ukončené 1/ })).toBeVisible();
  await expect(page.getByRole("button", { name: "Předchozí den s mými lety" })).toBeDisabled();

  // detail jako v Lety; Zpět vrátí na stejný den
  await page.locator(".denik-radek", { hasText: "OK-2817" }).click();
  await expect(page.locator(".obrazovka .let-hlava")).toContainText("OK-2817");
  await page.getByRole("button", { name: "Zpět" }).click();
  await expect(page).toHaveURL(/\/moje-lety\?den=/);
  await expect(obsah).toContainText("OK-2817");

  await page.getByRole("button", { name: "Další den s mými lety" }).click();
  await expect(page).toHaveURL(/\/moje-lety$/);
  await expect(obsah).toContainText("OK-6722");
});
