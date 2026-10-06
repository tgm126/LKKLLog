import { execSync } from "node:child_process";

import { expect, type Page } from "@playwright/test";

export const HESLO_ADMINA = "heslo-pro-e2e-test"; // backend/tests/e2e_priprava.py

/** Testovací databáze znovu do výchozího stavu (testy, které mění lety, si ji připraví samy). */
export function pripravitData() {
  execSync("uv run python -m tests.e2e_priprava", { cwd: "../backend", stdio: "inherit" });
}

export async function prihlasit(page: Page) {
  await page.goto("/prihlaseni");
  await page.getByLabel("E-mail").fill("admin@example.cz");
  await page.getByLabel("Heslo", { exact: true }).fill(HESLO_ADMINA);
  await page.getByRole("button", { name: "Přihlásit" }).click();
  await expect(page.getByRole("button", { name: "+ Nový let" })).toBeVisible();
}
