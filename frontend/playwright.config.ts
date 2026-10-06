// Klikací testy v rozměru mobilu proti skutečnému serveru (FastAPI vrací sestavený frontend)
// nad vlastní testovací databází lkkllog_e2e – viz backend/tests/e2e_priprava.py.
import { defineConfig, devices } from "@playwright/test";

const PORT = 8001;
export const ADRESA = `http://localhost:${PORT}`;
const ZAKLAD = process.env.LKKL_E2E_ZAKLAD ?? "postgresql://lkkllog:lkkllog@127.0.0.1:5432";

export default defineConfig({
  testDir: "e2e",
  workers: 1,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? "github" : "list",
  use: {
    ...devices["Pixel 7"],
    baseURL: ADRESA,
    locale: "cs-CZ",
    trace: "retain-on-failure",
  },
  webServer: {
    command: `uv run python -m tests.e2e_priprava && uv run uvicorn app.main:app --port ${PORT}`,
    cwd: "../backend",
    url: `${ADRESA}/api/health`,
    reuseExistingServer: false,
    env: {
      LKKL_DATABAZE: `${ZAKLAD}/lkkllog_e2e`,
      LKKL_ADRESA: ADRESA,
    },
  },
});
