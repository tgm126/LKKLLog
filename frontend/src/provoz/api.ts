// Můj provoz: letiště a osoby v provozu na dnešek pro tuto relaci (backend/app/muj_provoz.py,
// návrh docs/modul-muj-provoz.md).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type MujProvoz = {
  /** Moje letiště na dnešek (zvolené, jinak domovské). */
  letiste: { id: number; kod: string; nazev: string; domovske: boolean } | null;
  /** Osoby v provozu (filtr nabídky osob v posádce); prázdné = bez filtru. */
  osoby: number[];
};

export function useMujProvoz() {
  return useQuery({
    queryKey: ["muj-provoz"],
    queryFn: () => ziskat<MujProvoz>("/muj-provoz"),
    refetchInterval: 60_000, // přechod půlnoci: včerejší nastavení přestane platit
  });
}

/** Změna mého provozu; letiště mění i hlavičku (sluneční časy) a místa na páscích. */
export function useZmenitProvoz() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: (a: { cesta: string; data?: unknown }) =>
      poslat<MujProvoz>(`/muj-provoz${a.cesta}`, a.data),
    onSuccess: (provoz, a) => {
      qc.setQueryData(["muj-provoz"], provoz);
      if (a.cesta === "/letiste") {
        qc.invalidateQueries({ queryKey: ["den"] });
        qc.invalidateQueries({ queryKey: ["lety"] });
      }
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
}
