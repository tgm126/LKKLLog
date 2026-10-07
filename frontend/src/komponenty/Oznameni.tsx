import { createContext, useCallback, useContext, useEffect, useRef, useState, type ReactNode } from "react";

import { Tlacitko } from "./Tlacitko";
import "./Oznameni.css";

// Oznámení dole nad hlavní akcí: po VZLET, PŘISTÁL a T&G na 6 s s tlačítkem ZPĚT
// (docs/modul-lety.md 3.4); chyba (např. „Už vzlétl…“) bez ZPĚT.

export type Zprava = { text: string; zpet?: () => void; chyba?: boolean };

const DOBA_MS = 6000;

const Kontext = createContext<{
  zprava: Zprava | null;
  oznamit: (zprava: Zprava | null) => void;
}>({ zprava: null, oznamit: () => {} });

export function OznameniProvider({ children }: { children: ReactNode }) {
  const [zprava, setZprava] = useState<Zprava | null>(null);
  const casovac = useRef<ReturnType<typeof setTimeout>>(undefined);
  const oznamit = useCallback((nova: Zprava | null) => {
    clearTimeout(casovac.current);
    setZprava(nova);
    if (nova) casovac.current = setTimeout(() => setZprava(null), DOBA_MS);
  }, []);
  useEffect(() => () => clearTimeout(casovac.current), []);
  return <Kontext.Provider value={{ zprava, oznamit }}>{children}</Kontext.Provider>;
}

export function useOznamit() {
  return useContext(Kontext).oznamit;
}

/** Právě zobrazené oznámení (desktop: Ctrl+Z provede jeho ZPĚT). */
export function useZprava() {
  return useContext(Kontext);
}

export function Oznameni() {
  const { zprava, oznamit } = useContext(Kontext);
  if (!zprava) return null;
  return (
    <div className={`oznameni${zprava.chyba ? " chyba" : ""}`} role="status">
      <span>{zprava.text}</span>
      {zprava.zpet ? (
        <Tlacitko
          onClick={() => {
            zprava.zpet?.();
            oznamit(null);
          }}
        >
          ZPĚT
        </Tlacitko>
      ) : (
        <Tlacitko aria-label="Zavřít" onClick={() => oznamit(null)}>
          ✕
        </Tlacitko>
      )}
    </div>
  );
}
