// Režim zobrazení (podle zařízení / světlý / tmavý). Pamatuje si ho prohlížeč – je to
// nastavení zařízení, ne účtu (na telefonu venku světlý, doma na počítači třeba tmavý).
export type Rezim = "auto" | "svetly" | "tmavy";

export const REZIMY: { rezim: Rezim; nazev: string }[] = [
  { rezim: "auto", nazev: "Auto" }, // podle zařízení
  { rezim: "svetly", nazev: "Světlý" },
  { rezim: "tmavy", nazev: "Tmavý" },
];

const KLIC = "lkkl-rezim";

export function nacistRezim(): Rezim {
  try {
    const ulozeny = localStorage.getItem(KLIC);
    if (ulozeny === "svetly" || ulozeny === "tmavy") return ulozeny;
  } catch {
    // úložiště prohlížeče nemusí být dostupné (anonymní okno) – pak podle zařízení
  }
  return "auto";
}

export function nastavitRezim(rezim: Rezim): void {
  document.documentElement.dataset.rezim = rezim;
  try {
    localStorage.setItem(KLIC, rezim);
  } catch {
    // viz výše
  }
}
