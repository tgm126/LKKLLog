import { expect, test } from "@playwright/test";

import { prihlasit, prihlasitJenCteni, pripravitData } from "./pomocne";

// Export letů – PDF e-mailem adminům (docs/modul-export.md); mobil. Bez SMTP server e-mail
// jen zapíše do logu.

test.beforeAll(() => pripravitData());
test.afterAll(() => pripravitData()); // záznam odeslání omezuje další export na minutu

test("export: den z kalendáře i měsíc, odeslání s potvrzením", async ({ page }) => {
  await prihlasit(page);
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await page.getByRole("button", { name: "Export letů" }).click();
  await expect(page.getByText("přijde e-mailem na admin@example.cz")).toBeVisible();

  // Měsíc: běžící měsíc s lety, Zpět nic nepošle
  await page.getByRole("button", { name: "Měsíc", exact: true }).click();
  const mesice = page.getByRole("region", { name: "Měsíce" });
  await mesice.getByRole("button").first().click();
  const potvrzeni = page.getByRole("dialog");
  await expect(potvrzeni).toContainText(/\d+ let.* – na admin@example\.cz/);
  await potvrzeni.getByRole("button", { name: "Zpět" }).click();
  await expect(potvrzeni).toHaveCount(0);
  await expect(mesice.getByRole("button", { disabled: true }).first()).toBeVisible();

  // Den: jen dny s ukončenými lety
  await page.getByRole("button", { name: "Den", exact: true }).click();
  const kalendar = page.getByRole("region", { name: "Kalendář letů" });
  await kalendar.locator(".kalendar-den:enabled").last().click();
  await expect(potvrzeni).toContainText("admin@example.cz");
  await potvrzeni.getByRole("button", { name: "Poslat" }).click();
  await expect(page.getByRole("status")).toContainText("Odesláno na admin@example.cz");

  // Dvojklik / hned znovu: nejvýš jeden export za minutu
  await kalendar.locator(".kalendar-den:enabled").last().click();
  await potvrzeni.getByRole("button", { name: "Poslat" }).click();
  await expect(page.getByRole("status")).toContainText("další jde poslat za minutu");
});

test("export: jen ke čtení bez položky", async ({ page }) => {
  await prihlasitJenCteni(page);
  await page.getByRole("button", { name: "Nabídka uživatele" }).click();
  await expect(page.getByRole("button", { name: "Odhlásit" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Export letů" })).toHaveCount(0);
});
