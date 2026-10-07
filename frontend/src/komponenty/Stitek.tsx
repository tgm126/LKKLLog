import type { ReactNode } from "react";

import "./Stitek.css";

/** Barva jen pro význam (stav letu v detailu); „pasek“ = údaj v pásku letu (bílý s okrajem,
 *  vystoupí z barevného panelu). */
export type BarvaStitku = "modry" | "zeleny" | "cerveny" | "pasek";

export function Stitek({ barva, children }: { barva?: BarvaStitku; children: ReactNode }) {
  return <span className={["stitek", "cisla", barva].filter(Boolean).join(" ")}>{children}</span>;
}
