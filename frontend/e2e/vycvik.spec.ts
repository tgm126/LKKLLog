import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Editor výcviku na desktopu (docs/modul-osnovy.md): osnovy a úlohy, typy přezkoušení;
// osnovy kluzáků a typy přezkoušení z e2e_priprava.py (admin = FI(S) a FE(S) na kluzácích).

test.use({ viewport: { width: 1920, height: 1080 }, isMobile: false, hasTouch: false });
test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => {
  await prihlasit(page);
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: /^Výcvik/ }).click();
});

test("výcvik: účel úlohy, náhled nového letu, úprava názvu", async ({ page }) => {
  const panel = page.getByRole("complementary", { name: "Výcvik" });
  await expect(panel).toContainText(/3 osnovy · 37 úloh/);
  const matice = panel.getByLabel("Osnovy a úlohy");
  // přezkoušení už úlohy nemá – sloupce jen normální, výcvik, sólo
  await expect(matice.locator(".vycvik-zahlavi .vycvik-bunka")).toHaveText([
    "Normální",
    "Výcvik ·",
    "Sólo pod dozorem ·",
  ]);

  // zaškrtnout IU/4 i u normálního letu → náhled ho ukáže u normálního letu na kluzáku
  const normalni = matice.getByRole("checkbox", { name: "IU/4: Normální" });
  await expect(normalni).not.toBeChecked();
  await normalni.click(); // uloží se hned, zaškrtne se po odpovědi serveru
  await expect(normalni).toBeChecked();
  const nahled = panel.getByRole("region", { name: /Náhled: nový let/ });
  await nahled.getByRole("button", { name: "Normální", exact: true }).click();
  await nahled.getByRole("button", { name: "Kluzák", exact: true }).click();
  await expect(nahled).toContainText("Úloha · nepovinná");
  await expect(nahled.getByRole("button", { name: /IU\/4/ })).toBeVisible();
  // u přezkoušení místo úlohy typy přezkoušení
  await nahled.getByRole("button", { name: "Přezkoušení", exact: true }).click();
  await expect(nahled).toContainText("Přezkoušení · povinné (místo úlohy)");
  await expect(nahled.getByRole("button", { name: /^PC-CLOUD/ })).toBeVisible();
  await normalni.click();
  await expect(normalni).not.toBeChecked();

  // vybraná úloha: název se uloží po opuštění pole
  await matice.getByText("IU/12 Využití stoupavých proudů").click();
  const nazev = panel.getByLabel("Název (bez označení)");
  await nazev.fill("Využití stoupavých proudů a termiky");
  await nazev.press("Enter");
  await expect(matice).toContainText("IU/12 Využití stoupavých proudů a termiky");
  await expect(panel).toContainText("zatím v žádném letu"); // nepoužitá – jde smazat
});

test("výcvik: typy přezkoušení – kdo smí provést, nový typ a smazání", async ({ page }) => {
  const panel = page.getByRole("complementary", { name: "Výcvik" });
  await panel.getByRole("button", { name: "Typy přezkoušení" }).click();
  const matice = panel.getByLabel("Typy přezkoušení");
  // FE(S) má admin na kluzácích; pro letouny nikdo
  await expect(matice.locator(".vycvik-polozka", { hasText: "PC-SPL" })).not.toContainText("bez examinátora");
  await expect(matice.locator(".vycvik-polozka", { hasText: "PC-SEP" })).toContainText("bez examinátora");
  await matice.getByText("PC-CLOUD").click();
  await expect(panel.getByRole("region", { name: /Náhled: examinátor/ })).toContainText("Adam Admin");
  // kdo smí provést: jen oprávnění pro kategorii (kluzák)
  const kdo = panel.getByRole("region", { name: /Vybraný typ/ });
  await expect(kdo.getByRole("checkbox")).toHaveText([
    /FI\(S\)/,
    /FE\(S\) – examinátor/,
    /FE\(S\) – ověření/,
  ]);

  await panel.getByRole("button", { name: "Nový typ přezkoušení" }).click();
  await panel.getByLabel("Kód (např. PC-SEP)").fill("pc-test");
  await panel.getByLabel("Název (bez kódu)").fill("Zkušební typ");
  await panel.getByLabel("Kategorie letadla").selectOption({ label: "Kluzák" });
  await panel.getByRole("button", { name: "Založit" }).click();
  const novy = matice.locator(".vycvik-polozka", { hasText: "PC-TEST" });
  await expect(novy).toContainText("nikdo ho nesmí provést");
  await panel.getByRole("checkbox", { name: /FE\(S\) – examinátor/ }).click();
  await expect(novy).toContainText("FE(S) – examinátor kluzáků");
  await panel.getByRole("button", { name: "Smazat" }).click();
  await panel.getByRole("button", { name: "Smazat" }).click(); // potvrzení
  await expect(novy).toHaveCount(0);
});
