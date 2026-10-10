// Data správy osob ze serveru (backend/app/osoby.py, účty v prihlasovani.py).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat, type Schemata } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type UcetOsoby = Schemata["UcetOsoby"];
export type Osoba = Schemata["Osoba"];
export type OpravneniOsoby = Schemata["OpravneniOsoby"];
export type Opravneni = Schemata["Opravneni"];
export type DetailOsoby = Schemata["DetailOsoby"];

export type UdajeOsoby = Partial<
  Pick<Osoba, "jmeno" | "prijmeni" | "email" | "telefon" | "cislo_clena" | "clen" | "platny">
>;

export function useOsoby() {
  return useQuery({
    queryKey: ["osoby"],
    queryFn: () => ziskat<Schemata["Seznam"]>("/osoby"),
  });
}

export function useOsoba(id: number) {
  return useQuery({ queryKey: ["osoba", id], queryFn: () => ziskat<DetailOsoby>(`/osoby/${id}`) });
}

/** Úprava osoby (údaje, oprávnění, účet); po úspěchu nová data detailu i seznamu. */
export function useUpravitOsobu(id: number, poUlozeni?: () => void) {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: async (a: { cesta: string; data?: unknown }) => {
      const vysledek = await poslat<unknown>(a.cesta, a.data);
      // Odpověď /osoby/… je rovnou detail; po změně účtu se detail načte znovu.
      return a.cesta.startsWith("/osoby/") ? (vysledek as DetailOsoby) : null;
    },
    onSuccess: (detail) => {
      if (detail) qc.setQueryData(["osoba", id], detail);
      else qc.invalidateQueries({ queryKey: ["osoba", id] });
      qc.invalidateQueries({ queryKey: ["osoby"] });
      poUlozeni?.();
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
}

/** +420602123456 → „+420 602 123 456“ (jiné předvolby beze změny). */
export function telefonCitelne(telefon: string | null): string | null {
  const m = telefon?.match(/^(\+420)(\d{3})(\d{3})(\d{3})$/);
  return m ? m.slice(1).join(" ") : telefon;
}

/** „FI(S) – instruktor kluzáků“ → zkratka a vysvětlení. */
export function rozdelitNazev(nazev: string): [string, string | undefined] {
  const [zkratka, vysvetleni] = nazev.split(" – ");
  return [zkratka!, vysvetleni];
}
