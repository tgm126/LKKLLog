// Editor výcviku – data ze serveru (backend/app/vycvik.py, docs/modul-osnovy.md).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type Ucel = { id: number; kod: string; nazev: string; uloha_povinna: boolean };
export type Kategorie = { id: number; kod: string; nazev: string };
export type Uloha = {
  id: number;
  kod: string;
  nazev: string;
  platny: boolean;
  ucely: number[];
  lety: number;
};
export type Osnova = {
  id: number;
  kod: string;
  nazev: string;
  kategorie_id: number;
  platny: boolean;
  ulohy: Uloha[];
};
/** Typ přezkoušení; oprávnění = kdo ho smí provést. */
export type Typ = {
  id: number;
  kod: string;
  nazev: string;
  kategorie_id: number;
  platny: boolean;
  opravneni: number[];
  lety: number;
};
/** Oprávnění a kategorie, pro které se vydává. */
export type Opravneni = { id: number; nazev: string; kategorie: number[] };
export type Examinator = { osoba_id: number; jmeno: string; prijmeni: string; prezkouseni: number[] };

export type Vycvik = {
  ucely: Ucel[];
  kategorie: Kategorie[];
  osnovy: Osnova[];
  typy: Typ[];
  opravneni: Opravneni[];
  examinatori: Examinator[];
};

export function useVycvik() {
  return useQuery({ queryKey: ["vycvik"], queryFn: () => ziskat<Vycvik>("/vycvik") });
}

/** Změna v editoru: server vrátí celý nový stav; chyba se ukáže v oznámení. Nabídky nového
 *  letu (úlohy, typy) se po změně načtou znovu. */
export function useZmena() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const zmena = useMutation({
    mutationFn: ({ cesta, data }: { cesta: string; data?: unknown; potom?: (v: Vycvik) => void }) =>
      poslat<Vycvik>(`/vycvik${cesta}`, data ?? {}),
    onSuccess: (stav, { potom }) => {
      qc.setQueryData(["vycvik"], stav);
      qc.invalidateQueries({ queryKey: ["nabidky"] });
      potom?.(stav);
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
  return (cesta: string, data?: unknown, potom?: (v: Vycvik) => void) =>
    zmena.mutate({ cesta, data, potom });
}

export const popisOsnovy = (o: Osnova) => `${o.kod} – ${o.nazev}`;
export const popisUlohy = (u: Uloha, o: Osnova) => `${o.kod}/${u.kod} ${u.nazev}`;
