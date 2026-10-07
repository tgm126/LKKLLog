import { expect, test } from "@playwright/test";

import { prihlasit, pripravitData } from "./pomocne";

// Detail letu: ťuknutí na pásek, úprava na místě, zrušení s důvodem, obnovení.

test.beforeAll(() => pripravitData());
test.beforeEach(async ({ page }) => prihlasit(page));

test("detail: úprava, zrušení a obnovení", async ({ page }) => {
  await page.locator(".denik-radek.ukoncen", { hasText: "OK-CRA" }).click();
  await expect(page.locator(".obrazovka .let-hlava")).toContainText("OK-CRA");
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

  // Historie úprav v evidenci (rozbalí se ťuknutím).
  await page.getByRole("button", { name: /Historie/ }).click();
  await expect(page.getByText(/Úprava · Adam Admin/).first()).toBeVisible();
});

test("detail naplánovaného letu: úpravy, vzlet a přistání, časy a místa", async ({ page }) => {
  const blok = (nadpis: string) => page.locator(".blok", { hasText: nadpis });
  await page.locator(".let-par", { hasText: "OK-3819" }).getByText("OK-3819").click();
  await expect(page.locator(".obrazovka .let-hlava")).toContainText("OK-3819");
  await expect(page.getByText("Naplánovaný", { exact: true })).toBeVisible();

  // Posádka: jiný PIC.
  await blok("Posádka").getByRole("button", { name: /Nela Nová/ }).click();
  await page.getByRole("button", { name: "Já (Adam Admin)" }).click();
  await expect(blok("Posádka").getByRole("button", { name: /PIC\s*Adam Admin/ })).toBeVisible();

  // Úloha (u normálního letu nepovinná): osnova, pak úloha.
  await page.getByRole("button", { name: /^Úloha/ }).click();
  await page.getByRole("button", { name: /^II –/ }).click();
  await page.getByRole("button", { name: "II/2 Let po okruhu" }).click();
  await expect(page.getByRole("button", { name: /Úloha\s*II\/2 Let po okruhu/ })).toBeVisible();

  // Místo vzletu hledáním letiště (bez diakritiky).
  await page.getByRole("button", { name: /^Místo vzletu/ }).click();
  await page.locator(".uprava").getByRole("button", { name: "Hledat…" }).click();
  await page.getByLabel("Hledat letiště (kód nebo název)").fill("letn");
  await page.getByRole("button", { name: "LKLT Letňany" }).click();
  await expect(page.getByRole("button", { name: /Místo vzletu\s*LKLT/ })).toBeVisible();

  // Platí: místo aeroklubu osoba.
  await page.getByRole("button", { name: /Platí\s*Aeroklub/ }).click();
  await blok("Platba").getByRole("button", { name: "Hledat…" }).click();
  await blok("Platba").getByRole("button", { name: "Nela Nová" }).click();
  await expect(page.getByRole("button", { name: /Platí\s*Nela Nová/ })).toBeVisible();

  // VZLET z detailu, čas vzletu o dvě minuty dřív (přistání pak nepotřebuje dotaz na krátký let).
  await page.getByRole("button", { name: "Vzlet", exact: true }).click();
  await expect(page.getByRole("status")).toContainText(/OK-3819 vzlet \d\d:\d\d:\d\d/);
  await expect(page.getByText("Ve vzduchu", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: /^Vzlet\s*\d/ }).click();
  await page.getByRole("button", { name: "o minutu dřív" }).click();
  await page.getByRole("button", { name: "o minutu dřív" }).click();
  await page.getByRole("button", { name: "Uložit čas" }).click();
  await expect(page.getByRole("button", { name: "Uložit čas" })).toBeHidden();

  await page.getByRole("button", { name: "Přistál" }).click();
  await expect(page.getByText("Ukončený", { exact: true })).toBeVisible();
  await expect(page.getByRole("dialog")).toBeHidden();

  // Místo přistání v terénu popisem.
  await page.getByRole("button", { name: /^Místo přistání/ }).click();
  await page.getByLabel("Jiné místo (přistání do terénu)").fill("Pole u Brandýska");
  await page.getByRole("button", { name: "Uložit místo" }).click();
  await expect(
    page.getByRole("button", { name: /Místo přistání\s*Pole u Brandýska/ }),
  ).toBeVisible();

  // Čas přistání o minutu dřív zkrátí dobu letu.
  const doba = page.locator(".udaj", { hasText: "Doba" });
  const pred = await doba.textContent();
  await page.getByRole("button", { name: /^Přistání\s*\d/ }).click();
  await page.getByRole("button", { name: "o minutu dřív" }).click();
  await page.getByRole("button", { name: "Uložit čas" }).click();
  await expect(doba).not.toHaveText(pred!);

  // Zpět na přehled: let mezi ukončenými s novou posádkou a úlohou.
  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  const ukonceny = page
    .locator(".denik-radek.ukoncen", { hasText: "OK-3819" })
    .filter({ hasText: "II/2" });
  await expect(ukonceny).toContainText("Adam Admin");
  await expect(ukonceny.locator(".denik-pristani")).toHaveText("1");
});

test("zrušení naplánovaného vleku z detailu zruší kluzák i vlečnou", async ({ page }) => {
  await expect(page.getByRole("button", { name: /Zrušené 1/ })).toBeVisible();
  await page.locator(".let-par", { hasText: "OK-6722" }).getByText("OK-6722").click();
  await expect(page.locator(".obrazovka .let-hlava")).toContainText("OK-6722");

  // Rozmyšlení: Nerušit vrátí akce.
  await page.getByRole("button", { name: "Zrušit let" }).click();
  await page.getByRole("button", { name: "Nerušit" }).click();
  await page.getByRole("button", { name: "Zrušit let" }).click();
  await page.getByRole("button", { name: "Počasí" }).click();
  await expect(page.getByText("Zrušený", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "Zpět", exact: true }).click();
  await page.getByRole("button", { name: /Zrušené 3/ }).click();
  await expect(page.locator(".denik-radek.zrusen", { hasText: "OK-6722" })).toHaveCount(1);
  await expect(page.locator(".denik-radek.zrusen", { hasText: "OK-CRA" })).toHaveCount(1);
  await expect(page.locator(".let.naplanovan", { hasText: "OK-6722" })).toHaveCount(0);
});
