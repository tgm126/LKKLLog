import { expect, test, type Page } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Průvodce novým letem – varianty, které nepokrývá akce.spec.ts (aerovlek, místo, plátce).

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

const blok = (page: Page, nadpis: string) => page.locator(".blok", { hasText: nadpis });

test("průvodce: Zpět mezi kroky a Zavřít", async ({ page }) => {
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await expect(page.getByText("2 / 3 · Posádka")).toBeVisible();
  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  await expect(page.getByText("1 / 3 · Letadlo")).toBeVisible();
  await page.getByRole("button", { name: "Zavřít" }).click();
  await expect(page.getByRole("heading", { name: "Ve vzduchu 2" })).toBeVisible();
});

test("průvodce: proběhlý aerovlek z jiného letiště, platí aeroklub", async ({ page }) => {
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  // Po výběru zůstane jen vybraná osoba a Hledat…; ťuknutím na ni se nabídka znovu otevře.
  const pic = page.locator(".blok", { hasText: "PIC" });
  await expect(pic.getByRole("button")).toHaveText(["Já (Adam Admin)", "Hledat…"]);
  await pic.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await expect(pic.getByRole("button", { name: "Nela Nová" })).toBeVisible();
  await pic.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await page.getByRole("button", { name: "Dál" }).click();

  await page.getByRole("button", { name: "Aerovlek", exact: true }).click();
  await blok(page, "Vlečná").getByRole("button", { name: /^OK-CRA/ }).click();
  const vlekar = blok(page, "Vlekař");
  // Rychle se nabízí jen vlekaři (oprávnění Vlekař); ostatní najde Hledat…
  await expect(vlekar.getByRole("button", { name: "Nela Nová" })).toBeVisible();
  await expect(vlekar.getByRole("button", { name: /Adam Admin/ })).toHaveCount(0);
  await vlekar.getByRole("button", { name: "Hledat…" }).click();
  // Pilot kluzáku nesmí vlekat – v nabídce vlekaře není.
  await expect(vlekar.getByRole("button", { name: /Adam Admin/ })).toHaveCount(0);
  await vlekar.getByRole("button", { name: "Nela Nová" }).click();
  // Po výběru z hledání zpět na rychlou volbu: vybraná osoba a Hledat…
  await expect(vlekar.getByLabel("Hledat osobu")).toBeHidden();
  await expect(vlekar.getByRole("button", { name: "Nela Nová" })).toHaveAttribute("aria-pressed", "true");
  await expect(vlekar.getByRole("button", { name: "Hledat…" })).toBeVisible();

  // Vlečná v rozpracovaném pásku nahoře.
  await expect(page.locator(".let.rozpracovany .let-cas")).toContainText("OK-CRA");

  await page.getByRole("button", { name: /^Místo vzletu/ }).click();
  await page.locator(".uprava").getByRole("button", { name: "Hledat…" }).click();
  await page.getByLabel("Hledat letiště (kód nebo název)").fill("LKLT");
  await page.getByRole("button", { name: "LKLT Letňany" }).click();
  await expect(page.getByRole("button", { name: /Místo vzletu\s*LKLT Letňany/ })).toBeVisible();
  await page.getByRole("button", { name: /^Platí/ }).click();
  await page.getByRole("button", { name: "Aeroklub" }).click();
  await expect(page.getByRole("button", { name: /Platí\s*Aeroklub/ })).toBeVisible();

  await page.getByRole("button", { name: "Proběhlý let" }).click();
  await page.getByRole("button", { name: "Včera" }).click();
  // Vzlet, přistání kluzáku a přistání vlečné – další pole se po výběru otevře samo.
  for (const cas of ["10:00", "10:45", "10:10"]) {
    await page.getByRole("button", { name: "10", exact: true }).click();
    await page.getByRole("button", { name: cas }).click();
  }
  await expect(page.getByText('Doba letu 45"')).toBeVisible();
  await page.getByRole("button", { name: "Uložit proběhlý let" }).click();
  await expect(page.getByRole("status")).toHaveText(/OK-3819 proběhlý let 10:00–10:45 uložen/);

  // Včerejší lety: kluzák i vlečná z Letňan; místo přistání nezadané = moje letiště (LKKL,
  // na pásku se nevypisuje) pro oba lety vleku.
  const vcera = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
  type Let = { rejstrik: string; je_vlecny: boolean; misto_vzletu: string; misto_pristani: string };
  const { lety }: { lety: Let[] } = await (await page.request.get(`/api/lety?den=${vcera}`)).json();
  const kluzak = lety.find((l) => l.rejstrik === "OK-3819");
  const vlecna = lety.find((l) => l.rejstrik === "OK-CRA" && l.je_vlecny);
  expect(kluzak?.misto_vzletu).toBe("LKLT");
  expect(vlecna?.misto_vzletu).toBe("LKLT");
  expect(kluzak?.misto_pristani).toBeNull();
  expect(vlecna?.misto_pristani).toBeNull();
});

test("průvodce: naplánovaný přelet – místo přistání předem, trasa na pásku", async ({ page }) => {
  await page.getByRole("button", { name: "+ Nový let" }).click();
  await page.getByRole("button", { name: /^OK-3819/ }).click();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await page.getByRole("button", { name: "Dál" }).click();
  await page.getByRole("button", { name: "Naviják", exact: true }).click();
  await page.getByRole("button", { name: /^Místo přistání/ }).click();
  // Rychlá volba jen letiště s příznakem (a moje); ostatní najde Hledat…
  const mista = page.locator(".uprava");
  await expect(mista.getByRole("button", { name: "LKVO Vodochody" })).toHaveCount(0);
  await mista.getByRole("button", { name: "Hledat…" }).click();
  await page.getByLabel("Hledat letiště (kód nebo název)").fill("vodo");
  await expect(mista.getByRole("button", { name: "LKVO Vodochody" })).toBeVisible();
  await page.getByLabel("Hledat letiště (kód nebo název)").fill("");
  await mista.getByRole("button", { name: "LKLT Letňany" }).click();
  await expect(page.getByRole("button", { name: /Místo přistání\s*LKLT Letňany/ })).toBeVisible();
  await page.getByRole("button", { name: "Naplánovat" }).click();

  // Na pásku jen jedna strana trasy: kam letí.
  const pasek = page
    .locator(".let.naplanovan", { hasText: "OK-3819" })
    .filter({ hasText: "Adam Admin" });
  await expect(pasek.getByText("→ LKLT")).toBeVisible();
  // V detailu jde místo přistání upravit i před přistáním.
  await pasek.locator(".let-hlava").click();
  await expect(page.getByRole("button", { name: /Místo přistání\s*LKLT/ })).toBeVisible();
});
