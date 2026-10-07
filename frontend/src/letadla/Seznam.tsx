import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { poslat, ziskat } from "../api";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok } from "../komponenty/Obrazovka";
import { Oznameni, useOznamit } from "../komponenty/Oznameni";
import { Zaskrtavatka, Zaskrtavatko } from "../komponenty/Zaskrtavatko";
import "./Letadla.css";

// Letadla (docs/modul-letadla.md): seznam po kategoriích a přepínač mimo provoz (uloží se
// hned). Záložka jen pro právo „spravuje letadla“ (a admina); server ho hlídá také.

type Letadlo = {
  id: number;
  rejstrik: string;
  typ: string;
  kategorie: string;
  soukrome: boolean;
  mimo_provoz: boolean;
};

export function SeznamLetadel() {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  const { data: letadla, error } = useQuery({
    queryKey: ["letadla"],
    queryFn: () => ziskat<Letadlo[]>("/letadla"),
  });
  const zmenit = useMutation({
    mutationFn: (a: { id: number; mimo_provoz: boolean }) =>
      poslat<Letadlo>(`/letadla/${a.id}/mimo-provoz`, { mimo_provoz: a.mimo_provoz }),
    onSuccess: (letadlo) => {
      qc.setQueryData<Letadlo[]>(["letadla"], (l) =>
        l?.map((a) => (a.id === letadlo.id ? letadlo : a)),
      );
      qc.invalidateQueries({ queryKey: ["nabidky"] }); // průvodce nabízí jen letadla v provozu
      oznamit({
        text: `${letadlo.rejstrik} ${letadlo.mimo_provoz ? "mimo provoz" : "zpět v provozu"}`,
      });
    },
    onError: (e) => oznamit({ text: e.message, chyba: true }),
  });

  // Skupiny podle kategorie v pořadí ze serveru (kategorie → typ → rejstřík).
  const skupiny = new Map<string, Letadlo[]>();
  for (const a of letadla ?? []) skupiny.set(a.kategorie, [...(skupiny.get(a.kategorie) ?? []), a]);

  return (
    <main className="obsah">
      {error && <Hlaska>{error.message}</Hlaska>}
      <p className="male seda letadla-napoveda">
        Zaškrtnuté = mimo provoz: nenabízí se pro nové lety, stará data zůstávají.
      </p>
      {[...skupiny].map(([kategorie, polozky]) => (
        <Blok key={kategorie} nadpis={kategorie}>
          <div className="seznam-letadel">
            <Zaskrtavatka>
              {polozky.map((a) => (
                <Zaskrtavatko
                  key={a.id}
                  popisek={a.rejstrik}
                  pod={[a.typ, a.soukrome && "soukromé", a.mimo_provoz && "mimo provoz"]
                    .filter(Boolean)
                    .join(" · ")}
                  zaskrtnuto={a.mimo_provoz}
                  zakazano={zmenit.isPending}
                  zmenit={(mimo_provoz) => zmenit.mutate({ id: a.id, mimo_provoz })}
                />
              ))}
            </Zaskrtavatka>
          </div>
        </Blok>
      ))}
      <div className="oznameni-dole">
        <Oznameni />
      </div>
    </main>
  );
}
