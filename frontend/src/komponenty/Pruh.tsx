import type { ReactNode } from "react";

import { useAplikace } from "../uzivatel";
import "./Pruh.css";

export function Pruh({ children }: { children: ReactNode }) {
  return <div className="pruh">{children}</div>;
}

/** Fáze provozu (TESTOVACÍ PROVOZ…) – text nastavuje server; prázdný = bez pruhu. */
export function PruhProvozu() {
  const pruh = useAplikace()?.pruh;
  return pruh ? <Pruh>{pruh}</Pruh> : null;
}
