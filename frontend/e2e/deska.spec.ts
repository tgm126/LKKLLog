import { expect, test } from "@playwright/test";

import { prihlasit, prihlasitJenCteni, pripravitData } from "./pomocne";

// Provozní deska na desktopu (docs/modul-desktop.md) v rozměru věže 1920 × 1080 a notebooku
// 1366 × 768, ovládání myší; lety z e2e_priprava.py.

test.use({ viewport: { width: 1920, height: 1080 }, isMobile: false, hasTouch: false });
test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("deska: pásky, řada letadel, deník, souhrny a časová osa", async ({ page }) => {
  const pasky = page.getByRole("region", { name: "Pásky" });
  await expect(pasky).toContainText("Ve vzduchu 2");
  await expect(pasky).toContainText("Naplánované 3");
  // OK-MFV letí přes maximální dobu: červený pásek s varováním; T&G jen u motorového
  const mfv = pasky.locator(".pasek-deska.problem", { hasText: "OK-MFV" });
  await expect(mfv).toContainText("Přes maximální dobu letu");
  await expect(mfv.getByRole("button", { name: /T&G/ })).toHaveText("T&G 1");
  await expect(pasky.locator(".pasek-deska", { hasText: "OK-2817" }).getByRole("button", { name: /T&G/ })).toHaveCount(0);
  // Řádek štítků pod přihrádkami v pevných pozicích jako na mobilu; u vzletu šipka
  await expect(pasky.locator(".pasek-deska", { hasText: "OK-2817" }).locator(".stitky-pasku > span")).toHaveText([
    "",
    "naviják",
    "POB 2",
    "",
  ]);
  await expect(mfv.getByRole("img", { name: "vzlet" })).toBeVisible();
  // Vlek naplánovaný jako dvojice, VZLET jen u kluzáku
  const vlek = pasky.locator(".dvojice-deska", { hasText: "OK-6722" });
  await expect(vlek.locator(".pasek-deska")).toHaveCount(2);
  await expect(vlek.getByRole("button", { name: "Vzlet" })).toHaveCount(1);
  await expect(vlek).toContainText("vzlétne spolu s kluzákem");

  // Řada letadel: stav dneška, kde letadlo je (OK-CRA přistálo v Letňanech)
  const rada = page.getByRole("navigation", { name: "Letadla" });
  await expect(rada.getByRole("button", { name: /OK-MFV/ })).toContainText("letí");
  await expect(rada.getByRole("button", { name: /OK-CRA/ })).toContainText("na LKLT");
  await expect(rada.getByRole("button", { name: /OK-CUO 78/ })).toContainText("dnes nelétal");

  // Deník: řádek na let (ukončené, pod nimi zrušené)
  const denik = page.getByRole("region", { name: "Deník dne" });
  await expect(denik.locator(".radek-deniku:not(.zahlavi)")).toHaveCount(3);
  await expect(denik.locator(".radek-deniku.zrusen")).toContainText("OK-2817");

  // Souhrny: plachtařský (kluzáky a vleky) a motorový provoz zvlášť
  // (přistání jen u motorového – kluzák přistává jednou)
  const plachtari = page.getByRole("region", { name: "Plachtařský provoz" });
  await expect(plachtari).toContainText("OK-3819");
  await expect(plachtari.locator("thead th")).toHaveText(["Letadlo", "Lety", "Doba"]);
  const motorovy = page.getByRole("region", { name: "Motorový provoz" });
  await expect(motorovy).toContainText("OK-CRA");
  await expect(motorovy.locator("thead th")).toHaveText(["Letadlo", "Lety", "P", "Doba"]);

  // Časová osa: úsečka za každý let, který letěl nebo letí
  const osa = page.getByRole("region", { name: "Časová osa dne" });
  await expect(osa.getByRole("button", { name: /^Let / })).toHaveCount(4);
});

test("deska: akce z pásku, Ctrl+Z, detail v panelu a úprava", async ({ page }) => {
  const pasky = page.getByRole("region", { name: "Pásky" });
  const oznameni = page.getByRole("status");
  const mfv = () => pasky.locator(".pasek-deska", { hasText: "OK-MFV" });

  await mfv().getByRole("button", { name: /T&G/ }).click();
  await expect(mfv().getByRole("button", { name: /T&G/ })).toHaveText("T&G 2");
  await mfv().getByRole("button", { name: "Přistál" }).click();
  await expect(oznameni).toContainText(/OK-MFV přistání \d\d:\d\d:\d\d/);
  await expect(mfv()).toHaveCount(0);
  // Ctrl+Z = ZPĚT, dokud je oznámení vidět
  await page.keyboard.press("Control+z");
  await expect(mfv().getByRole("button", { name: "Přistál" })).toBeVisible();

  // Klik na pásek otevře detail v panelu; deska zůstává ovladatelná
  await pasky.locator(".pasek-deska", { hasText: "OK-2817" }).getByText("Petr Pilot").click();
  const detail = page.getByRole("complementary", { name: "Detail letu" });
  await expect(detail).toContainText("OK-2817");
  await expect(page).toHaveURL(/\/let\/\d+$/);
  await mfv().getByRole("button", { name: /T&G/ }).click();
  await expect(mfv().getByRole("button", { name: /T&G/ })).toHaveText("T&G 3");
  await expect(detail).toContainText("OK-2817");

  // Úprava na místě jako na mobilu
  await detail.getByRole("button", { name: /Poznámka/ }).click();
  await detail.getByLabel("Poznámka").fill("zkouška desky");
  await detail.getByRole("button", { name: "Uložit poznámku" }).click();
  await expect(detail.getByRole("button", { name: /Poznámka/ })).toContainText("zkouška desky");

  // Esc zavře panel
  await page.keyboard.press("Escape");
  await expect(detail).toBeHidden();
  await expect(page).toHaveURL(/\/$/);
});

test("deska: nový let klávesou N a z řady letadel, VZLET TEĎ", async ({ page }) => {
  const novy = page.getByRole("complementary", { name: "Nový let" });
  await page.keyboard.press("n");
  await expect(novy).toContainText("Nejdřív vyberte letadlo.");
  await page.keyboard.press("Escape");
  await expect(novy).toBeHidden();

  // Klik na letadlo na zemi = formulář s tímto letadlem
  await page.getByRole("navigation", { name: "Letadla" }).getByRole("button", { name: /OK-CUO 78/ }).click();
  await expect(novy.locator(".dlazdice.vybrana")).toContainText("OK-CUO 78");
  await expect(novy.locator(".panel-pata")).toContainText("Chybí: pilot");
  await novy.getByRole("button", { name: /^Já/ }).click();
  await expect(novy.locator(".panel-pata")).toContainText("Vše vyplněno");
  await novy.getByRole("button", { name: "Vzlet teď" }).click();

  await expect(page.getByRole("status")).toContainText(/OK-CUO 78 vzlet/);
  await expect(novy).toBeHidden();
  const pasek = page.getByRole("region", { name: "Pásky" }).locator(".pasek-deska", { hasText: "OK-CUO 78" });
  await expect(pasek).toContainText("Adam Admin");
});

test("deska na notebooku: souhrny za tlačítkem, jiný den bez pásků", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  const souhrny = page.getByRole("complementary", { name: "Souhrny dne" });
  await expect(souhrny).toBeHidden();
  await page.getByRole("button", { name: "Souhrny" }).click();
  await expect(souhrny).toBeVisible();

  await page.getByRole("button", { name: "Předchozí den" }).click();
  await expect(page.getByText(/^Prohlížíte/)).toBeVisible();
  await expect(page.getByRole("region", { name: "Pásky" })).toHaveCount(0);
  await expect(page.getByRole("region", { name: "Deník dne" })).toContainText("ukončené 0");
  await page.getByRole("button", { name: "Zpět na dnešek" }).click();
  await expect(page.getByRole("region", { name: "Pásky" })).toBeVisible();

  // Pod 1200 px mobilní přehled (pásky pod sebou)
  await page.setViewportSize({ width: 1100, height: 768 });
  await expect(page.locator(".let.problem", { hasText: "OK-MFV" })).toBeVisible();
});

test("deska jen ke čtení: bez akcí, N ani letadlo na zemi nic nezaloží, detail bez úprav", async ({
  page,
  context,
}) => {
  await context.clearCookies();
  await prihlasitJenCteni(page);
  await expect(page.locator(".lista-desky")).toContainText("Jen ke čtení");
  const pasky = page.getByRole("region", { name: "Pásky" });
  await expect(pasky.locator(".pasek-deska").first()).toBeVisible();
  await expect(pasky.getByRole("button")).toHaveCount(0);
  await expect(page.getByRole("button", { name: /Nový let/ })).toHaveCount(0);

  await page.keyboard.press("n");
  await page.getByRole("navigation", { name: "Letadla" }).getByRole("button", { name: /OK-CUO 78/ }).click();
  await expect(page.getByRole("complementary", { name: "Nový let" })).toHaveCount(0);

  await pasky.locator(".pasek-deska", { hasText: "OK-MFV" }).getByText("Olga Pilotka").click();
  const detail = page.getByRole("complementary", { name: "Detail letu" });
  await expect(detail).toContainText("OK-MFV");
  await expect(detail.getByRole("button", { name: /Poznámka|Přistál|Zrušit/ })).toHaveCount(0);
});
