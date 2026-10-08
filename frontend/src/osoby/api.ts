// Data správy osob ze serveru (backend/app/osoby.py, účty v prihlasovani.py).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type UcetOsoby = {
  smi_se_prihlasit: boolean;
  aktivni: boolean;
  admin: boolean;
  smi_odblokovat: boolean;
  spravuje_osoby: boolean;
  spravuje_letadla: boolean;
  zablokovano: boolean;
  ma_heslo: boolean;
};

export type Osoba = {
  id: number;
  jmeno: string;
  prijmeni: string;
  email: string | null;
  telefon: string | null;
  cislo_clena: string | null;
  clen: boolean;
  /** Platná osoba (v aplikaci „aktivní“): nabízí se v letech, smí se přihlásit. */
  platny: boolean;
  ucet: UcetOsoby | null;
  opravneni: OpravneniOsoby[];
};

/** Oprávnění, které osoba má: pro které kategorie letadel (id) a zda omezené. */
export type OpravneniOsoby = { id: number; omezene: boolean; kategorie: number[] };

/** Oprávnění z číselníku: kategorie letadel, pro které se smí vydat; lze_omezit = dává roli
 *  instruktora (jen tam má smysl „omezený“). */
export type Opravneni = {
  id: number;
  nazev: string;
  lze_omezit: boolean;
  kategorie: { id: number; nazev: string }[];
};

export type DetailOsoby = Osoba & {
  heslo_zmeneno: string | null;
  pozvanka_odeslana: string | null;
  posledni_prihlaseni: string | null;
  historie: { kdy: string; kdo: string; akce: string; popis: string | null }[];
};

export type UdajeOsoby = Partial<
  Pick<Osoba, "jmeno" | "prijmeni" | "email" | "telefon" | "cislo_clena" | "clen" | "platny">
>;

export function useOsoby() {
  return useQuery({
    queryKey: ["osoby"],
    queryFn: () => ziskat<{ osoby: Osoba[]; opravneni: Opravneni[] }>("/osoby"),
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
