import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Lety dne z backend/tests/e2e_priprava.py.
test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => {
  await prihlasit(page);
  await expect(page.getByRole("heading", { name: "Ve vzduchu 2" })).toBeVisible();
});

test("přehled letů dne", async ({ page }) => {
  // Hlavička: den a sluneční časy domovského letiště.
  await expect(page.getByRole("banner")).toContainText(/TB \d\d:\d\d · SR/);

  // Ve vzduchu: přes maximální dobu letu červeně s důvodem, stopky běží.
  const mfv = page.locator(".let", { hasText: "OK-MFV" });
  await expect(mfv).toHaveClass(/problem/);
  await expect(mfv).toContainText('Přes maximální dobu letu (1°30")');
  await expect(mfv).toContainText("T&G 1");
  const stopky = page.locator(".let", { hasText: "OK-2817" }).locator(".let-cas");
  const pred = await stopky.textContent();
  await expect(stopky).not.toHaveText(pred!, { timeout: 3000 });

  // Štítky v pevných pozicích: účel · způsob vzletu · POB · úloha; účel normální a vzlet
  // vlastní se nevypisují (pozice zůstane prázdná).
  await expect(
    page.locator(".let:is(.vzduch, .problem)", { hasText: "OK-2817" }).locator(".stitky-pasku > span"),
  ).toHaveText(["", "naviják", "POB 2", ""]);
  await expect(mfv.locator(".stitky-pasku > span")).toHaveText(["", "", "POB 1", ""]);
  await expect(mfv.locator(".let-cas")).toContainText(/\d\d:\d\d/);
  await expect(mfv.locator(".let-cas").getByRole("img", { name: "vzlet" })).toBeVisible();

  // Naplánované: vlek jako jeden dvojitý pásek.
  await expect(page.getByRole("heading", { name: "Naplánované 2" })).toBeVisible();
  const vlek = page.locator(".let", { hasText: "OK-6722" });
  await expect(vlek).toContainText("OK-CRA");
  await expect(vlek).toContainText("aerovlek");

  // Ukončené jako deník: čas, doba, počet přistání; letiště jen v detailu; celkový čas.
  await expect(page.getByRole("button", { name: /Ukončené 2/ })).toContainText('celkem 1°07"');
  const cra = page.locator(".denik-radek.ukoncen", { hasText: "OK-CRA" });
  await expect(cra.locator(".denik-pristani")).toHaveText("3");
  await expect(cra.locator(".denik-doba")).toHaveText('45"');
  await expect(cra.locator(".denik-podrobnosti")).toHaveText("POB 1 · dodatečně"); // POB vždy
  await expect(cra).not.toContainText("LKLT");

  // Zrušené jsou sbalené, ťuknutím se rozbalí.
  await expect(page.locator(".denik-radek.zrusen")).toHaveCount(0);
  await page.getByRole("button", { name: /Zrušené 1/ }).click();
  await expect(page.locator(".denik-radek.zrusen")).toHaveCount(1);
});
