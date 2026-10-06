import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import { ChybaApi } from "./api";
import { App } from "./App";
import { nacistRezim, nastavitRezim } from "./rezim";
import { KLIC_JA } from "./uzivatel";
import "./styly/tokeny.css";
import "./styly/zaklad.css";

nastavitRezim(nacistRezim());

// Vypršelé přihlášení (401) kdekoli = nepřihlášen → obrazovka přihlášení.
function pri401(chyba: Error) {
  if (chyba instanceof ChybaApi && chyba.status === 401) dotazy.setQueryData(KLIC_JA, null);
}

// Chybu požadavku (4xx) neopakovat; výpadek sítě nebo serveru zkusit znovu.
const dotazy: QueryClient = new QueryClient({
  queryCache: new QueryCache({ onError: pri401 }),
  mutationCache: new MutationCache({ onError: pri401 }),
  defaultOptions: {
    queries: {
      retry: (pokus, chyba) =>
        pokus < 3 && !(chyba instanceof ChybaApi && chyba.status >= 400 && chyba.status < 500),
    },
  },
});

createRoot(document.getElementById("aplikace")!).render(
  <StrictMode>
    <QueryClientProvider client={dotazy}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
