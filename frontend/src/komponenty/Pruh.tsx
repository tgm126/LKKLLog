import type { ReactNode } from "react";

import { useAplikace } from "../uzivatel";
import { Tlacitko } from "./Tlacitko";
import "./Pruh.css";

export function Pruh({ children }: { children: ReactNode }) {
  return <div className="pruh">{children}</div>;
}

/** Fáze provozu (TESTOVACÍ PROVOZ…) – text podle fáze v databázi; v ostrém provozu bez
 *  pruhu. Po nasazení nové verze nabídne její načtení. */
export function PruhProvozu() {
  const aplikace = useAplikace();
  return (
    <>
      {aplikace?.novaVerze && (
        <Pruh>
          Je k dispozici nová verze aplikace
          <Tlacitko onClick={() => window.location.reload()}>Načíst</Tlacitko>
        </Pruh>
      )}
      {aplikace?.pruh && <Pruh>{aplikace.pruh}</Pruh>}
    </>
  );
}
