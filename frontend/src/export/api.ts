// Export letů – PDF e-mailem adminům (backend/app/export.py, návrh docs/modul-export.md).
import { useMutation, useQuery } from "@tanstack/react-query";

import { poslat, ziskat, type Schemata } from "../api";
import { useOznamit } from "../komponenty/Oznameni";

export type NabidkaExportu = Schemata["NabidkaExportu"];
export type ExportIn = Schemata["ExportIn"];

export function useNabidkaExportu() {
  return useQuery({
    queryKey: ["export"],
    queryFn: () => ziskat<NabidkaExportu>("/export"),
  });
}

export function useExportovat() {
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: (data: ExportIn) => poslat<Schemata["Odeslano"]>("/export", data),
    onSuccess: (r) => oznamit({ text: `Odesláno na ${r.adresy.join(", ")}` }),
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });
}
