import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData, zeSpravy } from "./pomocne";

// Letadla (docs/modul-letadla.md): přepínač mimo provoz; admin má právo automaticky.

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("letadla: mimo provoz se v průvodci nedá vybrat", async ({ page }) => {
  await zeSpravy(page, "Letadla");
  const asw = page.getByRole("checkbox", { name: /^OK-6722/ });
  await asw.click();
  await expect(asw).toHaveAttribute("aria-checked", "true");
  await expect(page.getByRole("status")).toHaveText(/OK-6722 mimo provoz/);

  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  await page.getByRole("button", { name: "Nový let", exact: true }).click();
  await expect(page.getByRole("button", { name: /^OK-6722/ })).toBeDisabled();
  await page.getByRole("button", { name: "Zavřít" }).click();

  // Zpět do provozu.
  await zeSpravy(page, "Letadla");
  await asw.click();
  await expect(asw).toHaveAttribute("aria-checked", "false");
});
