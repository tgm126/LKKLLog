import type { ReactNode } from "react";

import { useAplikace } from "../uzivatel";
import { PruhProvozu } from "./Pruh";
import "./Vstupni.css";

/** Rám obrazovek bez přihlášení (přihlášení, nastavení hesla). */
export function Vstupni({
  nadpis,
  podnadpis,
  children,
}: {
  nadpis: string;
  podnadpis?: ReactNode;
  children: ReactNode;
}) {
  const verze = useAplikace()?.verze;
  return (
    <>
      <PruhProvozu />
      <main className="vstupni">
        <div className="vstupni-nazev">
          <h1 className="velke tucne">{nadpis}</h1>
          {podnadpis && <p className="seda">{podnadpis}</p>}
        </div>
        {children}
        <p className="vstupni-pata male seda">{verze}</p>
      </main>
    </>
  );
}
