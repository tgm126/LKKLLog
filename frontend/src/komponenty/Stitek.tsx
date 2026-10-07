import type { ReactNode } from "react";

import "./Stitek.css";

/** Barva jen pro význam (stav letu v detailu); „pasek“ = údaj v pásku letu (bílý s okrajem,
 *  vystoupí z barevného panelu); „oranzovy“ = upozornění (jiné letiště než domovské). */
export type BarvaStitku = "modry" | "zeleny" | "cerveny" | "oranzovy" | "pasek";

export function Stitek({
  barva,
  zkratit = false,
  children,
}: {
  barva?: BarvaStitku;
  /** Text se při nedostatku místa zkrátí „…“ (štítek nepřesáhne své místo). */
  zkratit?: boolean;
  children: ReactNode;
}) {
  return (
    <span className={["stitek", "cisla", barva].filter(Boolean).join(" ")}>
      {zkratit ? <span className="stitek-zkratit">{children}</span> : children}
    </span>
  );
}
