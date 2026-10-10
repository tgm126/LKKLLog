// Správa systému – jen admin (backend/app/sprava.py, návrh docs/modul-sprava.md).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat, type Schemata } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type DenSLety = Schemata["DenSLety"];
export type NastaveniSystemu = Schemata["NastaveniSystemu"];

export function useDnySLety() {
  return useQuery({
    queryKey: ["dny-s-lety"],
    queryFn: () => ziskat<DenSLety[]>("/sprava/dny-s-lety"),
  });
}

/** Smazání letů dne (procedura v databázi); obnoví kalendář i přehledy letů. */
export function useSmazatDen() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: (den: string) => poslat<Schemata["Smazano"]>("/sprava/smazat-den", { den }),
    onSuccess: () => {
      for (const klic of ["dny-s-lety", "lety", "den", "nabidky"]) qc.invalidateQueries({ queryKey: [klic] });
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
}

export function useNastaveniSystemu() {
  return useQuery({
    queryKey: ["nastaveni"],
    queryFn: () => ziskat<NastaveniSystemu>("/sprava/nastaveni"),
  });
}

/** Změna nastavení; pruh testovacího provozu se načte hned (jinak do minuty). */
export function useZmenitNastaveni() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: (data: NastaveniSystemu) => poslat<NastaveniSystemu>("/sprava/nastaveni", data),
    onSuccess: (n) => {
      qc.setQueryData(["nastaveni"], n);
      qc.invalidateQueries({ queryKey: ["aplikace"] });
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
}
