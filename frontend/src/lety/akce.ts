// Akce letu z pásku (VZLET, PŘISTÁL, T&G) s oznámením a Zpět (backend/app/lety.py).
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { poslat } from "../api";
import { hodinyMinutySekundy } from "../cas";
import { useOznamit } from "../komponenty/Oznameni";

export type Akce = "vzlet" | "pristani" | "tg";

export type Provedeno = { let_id: number; rejstrik: string; akce: string; cas: string | null };

const NAZEV: Record<Akce, string> = { vzlet: "vzlet", pristani: "přistání", tg: "T&G" };

export function useAkceLetu() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const obnovit = () => qc.invalidateQueries({ queryKey: ["lety"] });

  const zpet = useMutation({
    mutationFn: (a: { letId: number; akce: Akce }) =>
      poslat<Provedeno>(`/lety/${a.letId}/zpet`, { akce: a.akce }),
    onError: (e) => oznamit({ text: e.message, chyba: true }),
    onSettled: obnovit,
  });

  const akce = useMutation({
    mutationFn: (a: { letId: number; akce: Akce }) =>
      poslat<Provedeno>(`/lety/${a.letId}/${a.akce}`),
    onSuccess: (p, a) => oznamitAkci(oznamit, p, a.akce, () => zpet.mutate(a)),
    onError: (e) => oznamit({ text: e.message, chyba: true }),
    onSettled: obnovit,
  });

  return {
    provest: (letId: number, a: Akce) => akce.mutate({ letId, akce: a }),
    probiha: akce.isPending ? akce.variables : undefined,
    zpet: (letId: number, a: Akce) => zpet.mutate({ letId, akce: a }),
  };
}

/** „OK-CWF přistání 12:44:31“ s tlačítkem ZPĚT. */
export function oznamitAkci(
  oznamit: ReturnType<typeof useOznamit>,
  p: Provedeno,
  akce: Akce,
  zpet: () => void,
) {
  const cas = p.cas ? ` ${hodinyMinutySekundy(new Date(p.cas))}` : "";
  oznamit({ text: `${p.rejstrik} ${NAZEV[akce]}${cas}`, zpet });
}
