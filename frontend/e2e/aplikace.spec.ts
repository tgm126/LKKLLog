import { expect, test } from "@playwright/test";

import { prihlasit } from "./pomocne";

// Společné prvky aplikace: pruhy, režim zobrazení, nabídka uživatele, neznámá adresa.

test("pruh vývoje a nabídka nové verze po nasazení", async ({ page }) => {
  // Server „nasadí“ jinou verzi, zatímco je aplikace otevřená – ta nabídne načtení.
  let verze = "stara";
  await page.route("**/api/aplikace", async (route) => {
    const odpoved = await route.fetch();
    await route.fulfill({ response: odpoved, json: { ...(await odpoved.json()), verze } });
  });
  await page.clock.install();
  await prihlasit(page);
  const novaVerze = page.getByText("Je k dispozici nová verze aplikace");
  await expect(page.getByText("VÝVOJ – lokální databáze")).toBeVisible();
  await expect(novaVerze).toBeHidden();

  // Aplikace se ptá na verzi každou minutu.
  verze = "nova";
  await page.clock.fastForward(61_000);
  await expect(novaVerze).toBeVisible();
  await page.unroute("**/api/aplikace");
  await page.getByRole("button", { name: "Načíst" }).click();
  await expect(page.getByRole("button", { name: "+ Nový let" })).toBeVisible();
  await expect(novaVerze).toBeHidden();
});

test("režim zobrazení se pamatuje, ťuknutí vedle nabídky ji jen zavře", async ({ page }) => {
  await prihlasit(page);
  const uzivatel = page.getByRole("button", { name: "Nabídka uživatele" });
  const html = page.locator("html");

  for (const [nazev, rezim] of [
    ["Světlý", "svetly"],
    ["Auto", "auto"],
    ["Tmavý", "tmavy"],
  ] as const) {
    await uzivatel.click();
    await page.getByRole("button", { name: nazev }).click();
    await expect(html).toHaveAttribute("data-rezim", rezim);
  }
  await page.reload();
  await expect(html).toHaveAttribute("data-rezim", "tmavy");

  // Ťuknutí na zástin nad páskem zavře nabídku a detail letu neotevře.
  await uzivatel.click();
  await expect(page.getByText("admin@example.cz")).toBeVisible();
  const pasek = await page.locator(".let").first().boundingBox();
  await page.mouse.click(pasek!.x + 20, pasek!.y + 20);
  await expect(page.getByText("admin@example.cz")).toBeHidden();
  await expect(page).toHaveURL(/\/$/);
});

test("neznámá adresa vede na přehled letů", async ({ page }) => {
  await prihlasit(page);
  await page.goto("/neexistuje");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("button", { name: "+ Nový let" })).toBeVisible();
});

test("nedostupný server: srozumitelná hláška místo obecné chyby", async ({ page }) => {
  // Proxy před serverem odpoví 502, když aplikace neběží (nasazení, restart).
  await prihlasit(page);
  await page.route("**/api/lety/*/vzlet", (route) =>
    route.fulfill({ status: 502, contentType: "text/html", body: "<html>Bad Gateway</html>" }),
  );
  await page.locator(".let.naplanovan").first().getByRole("button", { name: "Vzlet" }).click();
  await expect(page.getByRole("status")).toHaveText(
    /Server je nedostupný \(možná se právě aktualizuje\)/,
  );
});
