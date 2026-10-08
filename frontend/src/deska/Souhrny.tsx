import { doba } from "../cas";
import { Blok } from "../komponenty/Obrazovka";
import "../komponenty/Tabulka.css";
import type { Pasek } from "../lety/api";

// Souhrny dne v pravém sloupci (docs/modul-desktop.md 3.4): plachtařský provoz (kluzáky
// a vleky) a motorový provoz (vše ostatní, i TMG a vlastní lety vlečné mimo vlek) – zařazení
// určuje databáze (v_let.druh_provozu, db/035). Tabulka
// letadel Lety · (P) · Doba (pořadí jako v deníku dne), celkem dole v patičce – u plachtařů
// zvlášť kluzáky a vleky, bez přistání (u kluzáku je přistání vždy jedno). Jen ukončené
// lety; počítá se z letů dne, nic se neukládá.

const minut = (lety: Pasek[]) => lety.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0);
const pristani = (lety: Pasek[]) => lety.reduce((s, l) => s + (l.pocet_pristani ?? 0), 0);

/** Řádek tabulky: lety · přistání (jen motorový) · doba (v patičce všechno tučně). */
function Hodnoty({ lety, sPristanim, celkem = false }: { lety: Pasek[]; sPristanim: boolean; celkem?: boolean }) {
  const Hodnota = celkem ? "b" : "span";
  return (
    <>
      <td>
        <Hodnota>{lety.length}</Hodnota>
      </td>
      {sPristanim && (
        <td>
          <Hodnota>{pristani(lety)}</Hodnota>
        </td>
      )}
      <td>
        <b>{doba(minut(lety))}</b>
      </td>
    </>
  );
}

function Tabulka({
  lety,
  poradi,
  sPristanim,
  celkem,
}: {
  lety: Pasek[];
  poradi: string[];
  /** Sloupec P (počet přistání) – jen motorový provoz. */
  sPristanim: boolean;
  /** Řádky patičky: popis a lety, které sečte. */
  celkem: [string, Pasek[]][];
}) {
  const radky = [...new Set(lety.map((l) => `${l.rejstrik}|${l.je_vlecny}`))]
    .map((klic) => {
      const [rejstrik, vlecny] = klic.split("|");
      return {
        rejstrik: rejstrik!,
        vleky: vlecny === "true",
        lety: lety.filter((l) => `${l.rejstrik}|${l.je_vlecny}` === klic),
      };
    })
    .sort((a, b) => poradi.indexOf(a.rejstrik) - poradi.indexOf(b.rejstrik));
  return (
    <table className="tabulka-souhrnu cisla">
      <thead>
        <tr className="zahlavi-tabulky">
          <th>Letadlo</th>
          <th>Lety</th>
          {sPristanim && <th title="Počet přistání">P</th>}
          <th>Doba</th>
        </tr>
      </thead>
      <tbody>
        {radky.map((r) => (
          <tr key={`${r.rejstrik}${r.vleky}`}>
            <td>
              <b>{r.rejstrik}</b>
              {r.vleky && <span className="male seda"> vleky</span>}
            </td>
            <Hodnoty lety={r.lety} sPristanim={sPristanim} />
          </tr>
        ))}
      </tbody>
      <tfoot>
        {celkem.map(([popis, x]) => (
          <tr key={popis} className="pata-tabulky">
            <td>{popis}</td>
            <Hodnoty lety={x} sPristanim={sPristanim} celkem />
          </tr>
        ))}
      </tfoot>
    </table>
  );
}

export function Souhrny({ lety, poradi }: { lety: Pasek[]; poradi: string[] }) {
  const ukoncene = lety.filter((l) => l.stav === "UKONCEN");
  const plachtari = ukoncene.filter((l) => l.druh_provozu === "PLACHTARSKY");
  const kluzaky = plachtari.filter((l) => !l.je_vlecny);
  const vleky = plachtari.filter((l) => l.je_vlecny);
  const motor = ukoncene.filter((l) => l.druh_provozu === "MOTOROVY");
  return (
    <>
      <Blok nadpis="Plachtařský provoz" popis="Plachtařský provoz">
        <Tabulka
          lety={[...kluzaky, ...vleky]}
          poradi={poradi}
          sPristanim={false}
          celkem={[
            ["Kluzáky", kluzaky],
            ["Vleky", vleky],
          ]}
        />
      </Blok>
      <Blok nadpis="Motorový provoz" popis="Motorový provoz">
        <Tabulka lety={motor} poradi={poradi} sPristanim celkem={[["Celkem", motor]]} />
      </Blok>
    </>
  );
}
