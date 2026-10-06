// Akce letu z pásku a detailu (VZLET, PŘISTÁL, T&G) s oznámením a Zpět (backend/app/lety.py).
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { poslat } from "../api";
import { hodinyMinutySekundy, stopky, ted } from "../cas";
import { Dialog } from "../komponenty/Dialog";
import { useOznamit } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useNabidky } from "./api";

export type Akce = "vzlet" | "pristani" | "tg";

export type Provedeno = { let_id: number; rejstrik: string; akce: string; cas: string | null };

/** Let pro PŘISTÁL: kvůli dotazu na let kratší než minuta je potřeba čas vzletu. */
export type LetKPristani = { id: number; rejstrik: string; cas_vzletu: string | null };

const NAZEV: Record<Akce, string> = { vzlet: "vzlet", pristani: "přistání", tg: "T&G" };

/** Nejkratší let, který se počítá bez dotazu (kratší: zrušit, nebo počítat jako 1 minutu). */
const MINUTA_MS = 60_000;

export function useAkceLetu() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const duvody = useNabidky().data?.duvody_zruseni;
  const [kratky, setKratky] = useState<LetKPristani | null>(null);
  const obnovit = () => {
    qc.invalidateQueries({ queryKey: ["lety"] });
    qc.invalidateQueries({ queryKey: ["let"] });
  };

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

  const zrusit = useMutation({
    mutationFn: (l: LetKPristani) => {
      const duvod = duvody?.find((d) => d.kod === "PRERUSENY_VZLET") ?? duvody?.[0];
      return poslat<Provedeno>(`/lety/${l.id}/zrusit`, { duvod_id: duvod?.id });
    },
    onSuccess: (p) => oznamit({ text: `${p.rejstrik} zrušen – přerušený vzlet` }),
    onError: (e) => oznamit({ text: e.message, chyba: true }),
    onSettled: obnovit,
  });

  const provest = (letId: number, a: Akce) => akce.mutate({ letId, akce: a });

  /** PŘISTÁL; let kratší než minuta se nejdřív zeptá, jestli ho zrušit, nebo počítat. */
  const pristat = (l: LetKPristani) => {
    const kratsi =
      l.cas_vzletu && ted().getTime() - new Date(l.cas_vzletu).getTime() < MINUTA_MS;
    if (kratsi) setKratky(l);
    else provest(l.id, "pristani");
  };

  const dialog = kratky && (
    <Dialog nadpis={`${kratky.rejstrik} – let kratší než minuta`} zavrit={() => setKratky(null)}>
      <p>
        Letí teprve {kratky.cas_vzletu && stopky(kratky.cas_vzletu, ted())}. Počítat ho jako let
        (zapíše se 1 minuta), nebo zrušit jako přerušený vzlet?
      </p>
      <Tlacitko
        varianta="zelene"
        hlavni
        onClick={() => {
          provest(kratky.id, "pristani");
          setKratky(null);
        }}
      >
        Počítat let
      </Tlacitko>
      <Tlacitko
        varianta="cervene"
        onClick={() => {
          zrusit.mutate(kratky);
          setKratky(null);
        }}
      >
        Zrušit – přerušený vzlet
      </Tlacitko>
      <Tlacitko varianta="obrys" onClick={() => setKratky(null)}>
        Zpět
      </Tlacitko>
    </Dialog>
  );

  return {
    provest,
    pristat,
    dialog,
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
