import type { ButtonHTMLAttributes } from "react";

import "./Tlacitko.css";

export type Varianta = "modre" | "zelene" | "svetle" | "obrys" | "cervene" | "bez-ramu";

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  varianta?: Varianta | Varianta[];
  /** Hlavní akce obrazovky: verzálky (PŘIHLÁSIT, VZLET). */
  hlavni?: boolean;
};

export function Tlacitko({ varianta = [], hlavni, className, type = "button", ...tlacitko }: Props) {
  const tridy = ["tl", ...[varianta].flat(), hlavni && "hlavni", className].filter(Boolean);
  return <button type={type} className={tridy.join(" ")} {...tlacitko} />;
}
