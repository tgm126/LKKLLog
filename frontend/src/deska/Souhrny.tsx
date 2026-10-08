import { doba } from "../cas";
import type { Pasek } from "../lety/api";

// Souhrny dne v pravém sloupci (docs/modul-desktop.md 3.4): plachtařský provoz (kluzáky
// a vleky) a motorový provoz (vše ostatní, i TMG a vlastní lety vlečné mimo vlek). Tabulka
// letadel Lety · P · Doba (pořadí jako v deníku dne), celkem dole v patičce – u plachtařů
// zvlášť kluzáky a vleky. Jen ukončené lety; počítá se z letů dne, nic se neukládá.

const minut = (lety: Pasek[]) => lety.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0);
const pristani = (lety: Pasek[]) => lety.reduce((s, l) => s + (l.pocet_pristani ?? 0), 0);

/** Řádek tabulky: lety · přistání · doba. */
function Hodnoty({ lety }: { lety: Pasek[] }) {
  return (
    <>
      <td>{lety.length}</td>
      <td>{pristani(lety)}</td>
      <td>
        <b>{doba(minut(lety))}</b>
      </td>
    </>
  );
}

function Tabulka({
  lety,
  poradi,
  celkem,
}: {
  lety: Pasek[];
  poradi: string[];
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
        <tr>
          <th>Letadlo</th>
          <th>Lety</th>
          <th title="Počet přistání">P</th>
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
            <Hodnoty lety={r.lety} />
          </tr>
        ))}
      </tbody>
      <tfoot>
        {celkem.map(([popis, x]) => (
          <tr key={popis}>
            <td className="male seda">{popis}</td>
            <Hodnoty lety={x} />
          </tr>
        ))}
      </tfoot>
    </table>
  );
}

export function Souhrny({ lety, poradi }: { lety: Pasek[]; poradi: string[] }) {
  const ukoncene = lety.filter((l) => l.stav === "UKONCEN");
  const kluzaky = ukoncene.filter((l) => l.kategorie_kod === "KLUZAK");
  const vleky = ukoncene.filter((l) => l.je_vlecny);
  const motor = ukoncene.filter((l) => l.kategorie_kod !== "KLUZAK" && !l.je_vlecny);
  return (
    <>
      <section className="karta-souhrnu" aria-label="Plachtařský provoz">
        <h2 className="nadpisek">Plachtařský provoz</h2>
        <Tabulka
          lety={[...kluzaky, ...vleky]}
          poradi={poradi}
          celkem={[
            ["Kluzáky", kluzaky],
            ["Vleky", vleky],
          ]}
        />
      </section>
      <section className="karta-souhrnu" aria-label="Motorový provoz">
        <h2 className="nadpisek">Motorový provoz</h2>
        <Tabulka lety={motor} poradi={poradi} celkem={[["Celkem", motor]]} />
      </section>
    </>
  );
}
