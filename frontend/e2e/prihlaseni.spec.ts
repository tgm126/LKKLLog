import { expect, request, test, type Page } from "@playwright/test";

import { ADRESA } from "../playwright.config";

const HESLO_ADMINA = "heslo-pro-e2e-test"; // backend/tests/e2e_priprava.py

const poleHeslo = (page: Page) => page.getByLabel("Heslo", { exact: true });

test("přihlášení s chybou a odhlášení", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/prihlaseni$/);
  await expect(page.getByRole("heading", { name: "AK Kladno Log" })).toBeVisible();

  await page.getByLabel("E-mail").fill("admin@example.cz");
  await poleHeslo(page).fill("spatne-heslo");
  await page.getByRole("button", { name: "Přihlásit" }).click();
  await expect(page.getByRole("alert")).toHaveText("Nesprávný e-mail nebo heslo.");
  await expect(poleHeslo(page)).toHaveValue("");
  await expect(poleHeslo(page)).toBeFocused();

  await poleHeslo(page).fill(HESLO_ADMINA);
  await page.getByRole("button", { name: "Ukázat" }).click();
  await expect(poleHeslo(page)).toHaveAttribute("type", "text");
  await page.getByRole("button", { name: "Přihlásit" }).click();
  await expect(page).toHaveURL(`${ADRESA}/`);
  const uzivatel = page.getByRole("button", { name: "Nabídka uživatele" });
  await expect(uzivatel).toHaveText("AA");

  // Přihlášení vydrží načtení stránky znovu.
  await page.reload();
  await expect(uzivatel).toHaveText("AA");

  await uzivatel.click();
  await page.getByRole("button", { name: "Tmavý" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-rezim", "tmavy");
  // Po volbě režimu se nabídka zavře.
  await expect(page.getByRole("button", { name: "Odhlásit" })).toBeHidden();
  await uzivatel.click();
  await page.getByRole("button", { name: "Odhlásit" }).click();
  await expect(page.getByRole("heading", { name: "AK Kladno Log" })).toBeVisible();
  await expect(page).toHaveURL(/\/prihlaseni$/);
});

test("nastavení hesla odkazem od admina", async ({ page }) => {
  // Admin si vyžádá odkaz pro Nelu (ve fázi 1 ho předává osobně).
  const api = await request.newContext({ baseURL: ADRESA, extraHTTPHeaders: { Origin: ADRESA } });
  await api.post("/api/prihlaseni", { data: { email: "admin@example.cz", heslo: HESLO_ADMINA } });
  const ucty: { osoba_id: number; email: string }[] = await (await api.get("/api/ucty")).json();
  const nela = ucty.find((u) => u.email === "nova@example.cz")!;
  const { odkaz } = await (await api.post(`/api/ucty/${nela.osoba_id}/pozvanka`)).json();
  await api.dispose();

  await page.goto(odkaz);
  await expect(page.getByRole("heading", { name: "Nastavení hesla" })).toBeVisible();
  await expect(page.getByText("Nela Nová")).toBeVisible();
  const ulozit = page.getByRole("button", { name: "Uložit a přihlásit" });
  await expect(ulozit).toBeDisabled();

  const heslo = page.getByLabel("Nové heslo");
  await heslo.fill("kratke");
  await expect(page.getByText("Ještě 4 znaky.")).toBeVisible();
  await expect(ulozit).toBeDisabled();
  await heslo.fill("nove-heslo-pro-nelu");
  await ulozit.click();
  await expect(page.getByRole("button", { name: "Nabídka uživatele" })).toHaveText("NN");

  // Odkaz je jednorázový.
  await page.goto(odkaz);
  await expect(page.getByRole("heading", { name: "Nastavení hesla" })).toBeVisible();
  await expect(page.getByRole("alert")).toHaveText(
    "Odkaz neplatí nebo vypršel. Požádejte admina o nový.",
  );
});

test("po přihlášení zpět, kam mířil", async ({ page }) => {
  await page.goto("/?den=2026-10-06");
  await expect(page).toHaveURL(/\/prihlaseni\?dalsi=%2F%3Fden%3D2026-10-06$/);
  await page.getByLabel("E-mail").fill("admin@example.cz");
  await poleHeslo(page).fill(HESLO_ADMINA);
  await page.getByRole("button", { name: "Přihlásit" }).click();
  await expect(page).toHaveURL(`${ADRESA}/?den=2026-10-06`);
});
