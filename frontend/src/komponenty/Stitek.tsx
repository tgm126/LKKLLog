import type { ReactNode } from "react";

import "./Stitek.css";

/** obrys = doplňující údaj mimo stálé pořadí (bez výplně, jen rámeček) */
export type BarvaStitku = "modry" | "zeleny" | "oranzovy" | "cerveny" | "obrys";

export function Stitek({ barva, children }: { barva?: BarvaStitku; children: ReactNode }) {
  return <span className={["stitek", "cisla", barva].filter(Boolean).join(" ")}>{children}</span>;
}

/** Řádek štítků; prázdné položky vynechá, bez štítků nevykreslí nic. */
export function Stitky({ children }: { children: ReactNode[] }) {
  const stitky = children.filter(Boolean);
  return stitky.length ? <div className="stitky">{stitky}</div> : null;
}
