import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Můj provoz (docs/modul-muj-provoz.md): letiště a osoby v provozu na dnešek pro relaci.
// Každý test se přihlašuje znovu = nová relace bez nastavení.

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("můj provoz: letiště pro dnešek", async ({ page }) => {
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: /^Letiště\s*LKKL Kladno/ }).click();
  await expect(page.getByRole("heading", { name: "Letiště pro dnešek" })).toBeVisible();
  await page.getByRole("button", { name: "LKLT Letňany" }).click();

  // Zpět na lety; v hlavičce štítek jiného letiště.
  const stitek = page.getByRole("button", { name: "Letiště pro dnešek: LKLT Letňany" });
  await expect(stitek).toBeVisible();

  // Nový let má místo vzletu moje letiště.
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await page.getByRole("button", { name: "Dál" }).click();
  await expect(page.getByRole("button", { name: /Místo vzletu\s*LKLT Letňany/ })).toBeVisible();
  await page.goto("/"); // z průvodce zpět na přehled

  // Ťuknutím na štítek zpět na domovské.
  await stitek.click();
  await page.getByRole("button", { name: "LKKL Kladno" }).click();
  await expect(page.getByRole("heading", { name: "Ve vzduchu 2" })).toBeVisible();
  await expect(stitek).toHaveCount(0);
});

test("můj provoz: osoby v provozu", async ({ page }) => {
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: /^Osoby v provozu\s*všechny/ }).click();
  await page.getByRole("checkbox", { name: "Nová Nela" }).click();
  await expect(page.getByText("1 vybraná")).toBeVisible();
  await page.getByRole("button", { name: "Zpět", exact: true }).click();

  // Rychlá volba jen z osob v provozu (a Já); Hledat… najde i ostatní.
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  const pic = page.locator(".blok", { hasText: "PIC" });
  await expect(pic.getByText("jen osoby v provozu (1)")).toBeVisible();
  await expect(pic.getByRole("button")).toHaveText(["Já (Adam Admin)", "Nela Nová", "Hledat…"]);
  await pic.getByRole("button", { name: "Hledat…" }).click();
  await page.getByLabel("Hledat osobu").fill("petr");
  await expect(pic.getByRole("button", { name: "Petr Pilot" })).toBeVisible();
  await page.goto("/"); // z průvodce zpět na přehled

  // Zrušit výběr = zase všichni.
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: /^Osoby v provozu\s*1/ }).click();
  await page.getByRole("button", { name: "Zrušit výběr – nabízet všechny" }).click();
  await expect(page.getByText("0 vybraných")).toBeVisible();
});
