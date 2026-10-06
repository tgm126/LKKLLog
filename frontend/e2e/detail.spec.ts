import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Detail letu: ťuknutí na pásek, úprava na místě, zrušení s důvodem, obnovení, další let.

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("detail: úprava, zrušení, obnovení a další let odsud", async ({ page }) => {
  await page.locator(".let.ukoncen", { hasText: "3 přistání" }).click();
  await expect(page.getByRole("heading", { name: /OK-CRA/ })).toBeVisible();
  await expect(page.getByText("Ukončený")).toBeVisible();
  await expect(page.getByRole("button", { name: /Místo přistání\s*LKLT/ })).toBeVisible();

  // Poznámka ťuknutím na údaj.
  await page.getByRole("button", { name: /Poznámka\s*ťuknutím přidat/ }).click();
  await page.getByLabel("Poznámka").fill("Přelet na Letňany");
  await page.getByRole("button", { name: "Uložit poznámku" }).click();
  await expect(page.getByRole("button", { name: /Poznámka\s*Přelet na Letňany/ })).toBeVisible();

  // Přistání celkem.
  await page.getByRole("button", { name: /Přistání celkem\s*3/ }).click();
  await page.locator(".volby-pocet").getByRole("button", { name: "2", exact: true }).click();
  await expect(page.getByRole("button", { name: /Přistání celkem\s*2/ })).toBeVisible();

  // Zrušení s důvodem a obnovení.
  await page.getByRole("button", { name: "Zrušit let" }).click();
  await page.getByRole("button", { name: "Počasí" }).click();
  await expect(page.getByText("Zrušený", { exact: true })).toBeVisible();
  await expect(page.getByText(/Zrušil.*Počasí/)).toBeVisible();
  await page.getByRole("button", { name: "Obnovit let" }).click();
  await expect(page.getByText("Ukončený")).toBeVisible();

  // Historie úprav v evidenci.
  await expect(page.getByText(/Úprava · Adam Admin/).first()).toBeVisible();

  // Další let odsud: naplánovaný, místo vzletu = místo přistání.
  await page.getByRole("button", { name: "Další let odsud" }).click();
  await expect(page.getByRole("status")).toHaveText(/OK-CRA naplánován/);
  await expect(page.locator(".let.naplanovan", { hasText: "z LKLT" })).toContainText("OK-CRA");
});
