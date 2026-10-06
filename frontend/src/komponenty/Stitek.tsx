import type { ReactNode } from "react";

import "./Stitek.css";

/** Štítek stavu (detail letu); barva jen pro význam. */
export type BarvaStitku = "modry" | "zeleny" | "oranzovy" | "cerveny";

export function Stitek({ barva, children }: { barva?: BarvaStitku; children: ReactNode }) {
  return <span className={["stitek", "cisla", barva].filter(Boolean).join(" ")}>{children}</span>;
}
