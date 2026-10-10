// Editor výcviku – data ze serveru (backend/app/vycvik.py, docs/modul-osnovy.md).
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat, type Schemata } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type Ucel = Schemata["Ucel"];
export type Kategorie = Schemata["Polozka"];
export type Uloha = Schemata["Uloha"];
export type Osnova = Schemata["Osnova"];
export type Typ = Schemata["Typ"];
export type Opravneni = Schemata["DruhOpravneni"];
export type Examinator = Schemata["Examinator"];
export type Vycvik = Schemata["Vycvik"];

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
