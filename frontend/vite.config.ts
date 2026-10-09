import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Při vývoji běží frontend na :5173 a rozhraní /api přeposílá serveru FastAPI na :8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
  // Jednotkové testy (vitest) jen ve src/ – soubory e2e/*.spec.ts patří Playwrightu.
  test: { include: ["src/**/*.test.ts"] },
});
