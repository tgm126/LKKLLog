import type { ReactNode } from "react";
import { useNavigate } from "react-router";

import type { Klik } from "../komponenty/klavesnice";
import { Tlacitko } from "../komponenty/Tlacitko";
import type { useAkceLetu } from "../lety/akce";
import type { Pasek, Stav } from "../lety/api";
import { dvojice, podle } from "../lety/poradi";
import { useJenCteni } from "../uzivatel";
import { PasekDeska } from "./PasekDeska";

// Sloupec pásků (docs/modul-desktop.md 3.2): ve vzduchu (nejdéle letící nahoře), pod nimi
// naplánované (v pořadí založení); vlek jako dvojitý pásek. Klik na pásek otevře detail.

type Akce = ReturnType<typeof useAkceLetu>;

export function Pasky({
  lety,
  mojeKod,
  vybranyId,
  akce,
}: {
  lety: Pasek[];
  mojeKod: string | undefined;
  vybranyId: number | null;
  akce: Akce;
}) {
  const navigate = useNavigate();
  const jenCteni = useJenCteni();
  const ve = (stav: Stav) => lety.filter((l) => l.stav === stav);
  const veVzduchu = dvojice(ve("VE_VZDUCHU").sort(podle((l) => l.vzlet_namereno)));
  const naplanovane = dvojice(ve("NAPLANOVAN").sort(podle((l) => l.zalozeno)));
  const pocet = (d: Pasek[][]) => d.reduce((s, x) => s + x.length, 0);
  const otevrit =
    (id: number): Klik =>
    (e) => {
      if (!(e.target as HTMLElement).closest("button")) navigate(`/let/${id}`);
    };

  const skupina = (d: Pasek[], obsah: (l: Pasek, i: number) => ReactNode) => {
    const pasky = d.map((l, i) => (
      <PasekDeska
        key={l.id}
        let={l}
        mojeKod={mojeKod}
        vybrany={l.id === vybranyId}
        onClick={otevrit(l.id)}
      >
        {/* jen ke čtení: bez akcí (přihrádka zůstane prázdná) */}
        {!jenCteni && obsah(l, i)}
      </PasekDeska>
    ));
    return (
      <div key={d[0]!.id} className={d.length > 1 ? "dvojice-deska" : undefined}>
        {pasky}
      </div>
    );
  };

  return (
    <>
      <h2 className="nadpis-sloupce">
        <span className="nadpisek">Ve vzduchu {pocet(veVzduchu)}</span>
        <span className="male seda">nejdéle letící nahoře</span>
      </h2>
      {veVzduchu.length === 0 && <p className="prazdny-sloupec male seda">Nikdo neletí.</p>}
      {veVzduchu.map((d) =>
        skupina(d, (l) => (
          <>
            {/* T&G jen motorová letadla, TMG a UL, ne vlečná (při vleku nedělá) */}
            {l.kategorie_kod !== "KLUZAK" && !l.je_vlecny && (
              <Tlacitko
                varianta="obrys"
                disabled={akce.bezi(l.id, "tg")}
                onClick={() => akce.provest(l.id, "tg")}
              >
                T&amp;G <span className="cisla">{l.pocet_tg}</span>
              </Tlacitko>
            )}
            <Tlacitko
              varianta="zelene"
              hlavni
              disabled={akce.bezi(l.id, "pristani")}
              onClick={() => akce.pristat(l)}
            >
              Přistál
            </Tlacitko>
          </>
        )),
      )}
      <h2 className="nadpis-sloupce">
        <span className="nadpisek">Naplánované {pocet(naplanovane)}</span>
        <span className="male seda">v pořadí založení</span>
      </h2>
      {naplanovane.length === 0 && <p className="prazdny-sloupec male seda">Nic naplánováno.</p>}
      {naplanovane.map((d) =>
        skupina(d, (l, i) =>
          // u vleku jeden VZLET pro oba lety (u kluzáku); vlečná vzlétne s ním
          i === 0 ? (
            <Tlacitko
              varianta="modre"
              hlavni
              disabled={akce.bezi(l.id, "vzlet")}
              onClick={() => akce.provest(l.id, "vzlet")}
            >
              Vzlet
            </Tlacitko>
          ) : (
            <span className="spolecne">vzlétne spolu s kluzákem</span>
          ),
        ),
      )}
    </>
  );
}
