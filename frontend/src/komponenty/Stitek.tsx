import type { ReactNode } from "react";

import "./Stitek.css";

export type BarvaStitku = "modry" | "zeleny" | "oranzovy" | "cerveny";

export function Stitek({ barva, children }: { barva?: BarvaStitku; children: ReactNode }) {
  return <span className={["stitek", "cisla", barva].filter(Boolean).join(" ")}>{children}</span>;
}

/** Řádek štítků; prázdné položky vynechá, bez štítků nevykreslí nic. */
export function Stitky({ children }: { children: ReactNode[] }) {
  const stitky = children.filter(Boolean);
  return stitky.length ? <div className="stitky">{stitky}</div> : null;
}
