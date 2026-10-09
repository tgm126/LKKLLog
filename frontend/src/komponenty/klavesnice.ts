// Klikací prvek, který není <button> (pásek letu, řádek deníku, řádek editoru, úsečka na
// časové ose): dostupný i z klávesnice – fokus tabulátorem, Enter nebo mezerník jako klik
// (code review 9. 10. 2026, F7). Klávesa stisknutá v tlačítku uvnitř (PŘISTÁL) patří jemu.
// Role: co otevírá jinou obrazovku (pásek → detail letu) je odkaz, co mění stav na místě
// (řádek editoru → výběr) je tlačítko; čtečka i testy je tak odliší od skutečných tlačítek.
import type { KeyboardEvent, SyntheticEvent } from "react";

export type Klik = (e: SyntheticEvent<Element>) => void;

export function jakoTlacitko(onClick: Klik | undefined, role: "button" | "link" = "button") {
  if (!onClick) return {};
  return {
    role,
    tabIndex: 0,
    onClick,
    onKeyDown: (e: KeyboardEvent<Element>) => {
      if (e.target !== e.currentTarget || (e.key !== "Enter" && e.key !== " ")) return;
      e.preventDefault();
      onClick(e);
    },
  };
}
