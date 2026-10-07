// Pořadí a seskupení letů v přehledu dne – mobil (stranky/Lety.tsx) i desktop (deska/).
import type { Pasek } from "./api";

/** Řazení podle textového údaje (čas ISO), prázdné první. */
export const podle =
  (klic: (l: Pasek) => string | null, sestupne = false) =>
  (a: Pasek, b: Pasek) =>
    (klic(a) ?? "").localeCompare(klic(b) ?? "") * (sestupne ? -1 : 1);

/** Vlek (kluzák + jeho vlečná ve stejném stavu) jako jedna dvojice – naplánovaný i ve vzduchu. */
export function dvojice(lety: Pasek[]): Pasek[][] {
  const podleId = new Map(lety.map((l) => [l.id, l]));
  const vlecne = new Set(
    lety.flatMap((l) => (l.vlecny_let_id && podleId.has(l.vlecny_let_id) ? [l.vlecny_let_id] : [])),
  );
  return lety
    .filter((l) => !vlecne.has(l.id))
    .map((l) => {
      const vlecna = l.vlecny_let_id ? podleId.get(l.vlecny_let_id) : undefined;
      return vlecna ? [l, vlecna] : [l];
    });
}
