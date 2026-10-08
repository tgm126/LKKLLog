import { doba } from "../cas";
import { Blok } from "../komponenty/Obrazovka";
import "../komponenty/Tabulka.css";
import type { RadekSouhrnu } from "../lety/api";

// Souhrny dne v pravém sloupci (docs/modul-desktop.md 3.4): plachtařský provoz (kluzáky
// a vleky) a motorový provoz (vše ostatní, i TMG a vlastní lety vlečné mimo vlek). Řádky po
// letadlech počítá databáze (v_souhrn_dne, db/036 – jen ukončené lety, zařazení podle
// v_let.druh_provozu); tady se jen vykreslí: Letadlo · Lety · (P) · Doba v pořadí jako
// v deníku dne, celkem dole v patičce – u plachtařů zvlášť kluzáky a vleky, bez přistání.

/** Součet řádků do patičky. */
const soucet = (radky: RadekSouhrnu[]) => ({
  lety: radky.reduce((s, r) => s + r.lety, 0),
  pristani: radky.reduce((s, r) => s + r.pristani, 0),
  minut: radky.reduce((s, r) => s + r.minut, 0),
});

/** Řádek tabulky: lety · přistání (jen motorový) · doba (v patičce všechno tučně). */
function Hodnoty({
  r,
  sPristanim,
  celkem = false,
}: {
  r: { lety: number; pristani: number; minut: number };
  sPristanim: boolean;
  celkem?: boolean;
}) {
  const Hodnota = celkem ? "b" : "span";
  return (
    <>
      <td>
        <Hodnota>{r.lety}</Hodnota>
      </td>
      {sPristanim && (
        <td>
          <Hodnota>{r.pristani}</Hodnota>
        </td>
      )}
      <td>
        <b>{doba(r.minut)}</b>
      </td>
    </>
  );
}

function Tabulka({
  radky,
  poradi,
  sPristanim,
  celkem,
}: {
  radky: RadekSouhrnu[];
  poradi: string[];
  /** Sloupec P (počet přistání) – jen motorový provoz. */
  sPristanim: boolean;
  /** Řádky patičky: popis a řádky, které sečte. */
  celkem: [string, RadekSouhrnu[]][];
}) {
  const serazene = [...radky].sort(
    (a, b) => poradi.indexOf(a.rejstrik) - poradi.indexOf(b.rejstrik) || Number(a.je_vlecny) - Number(b.je_vlecny),
  );
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
        {serazene.map((r) => (
          <tr key={`${r.rejstrik}${r.je_vlecny}`}>
            <td>
              <b>{r.rejstrik}</b>
              {r.je_vlecny && <span className="male seda"> vleky</span>}
            </td>
            <Hodnoty r={r} sPristanim={sPristanim} />
          </tr>
        ))}
      </tbody>
      <tfoot>
        {celkem.map(([popis, x]) => (
          <tr key={popis} className="pata-tabulky">
            <td>{popis}</td>
            <Hodnoty r={soucet(x)} sPristanim={sPristanim} celkem />
          </tr>
        ))}
      </tfoot>
    </table>
  );
}

export function Souhrny({ souhrn, poradi }: { souhrn: RadekSouhrnu[]; poradi: string[] }) {
  const plachtari = souhrn.filter((r) => r.druh_provozu === "PLACHTARSKY");
  const motor = souhrn.filter((r) => r.druh_provozu === "MOTOROVY");
  return (
    <>
      <Blok nadpis="Plachtařský provoz" popis="Plachtařský provoz">
        <Tabulka
          radky={plachtari}
          poradi={poradi}
          sPristanim={false}
          celkem={[
            ["Kluzáky", plachtari.filter((r) => !r.je_vlecny)],
            ["Vleky", plachtari.filter((r) => r.je_vlecny)],
          ]}
        />
      </Blok>
      <Blok nadpis="Motorový provoz" popis="Motorový provoz">
        <Tabulka radky={motor} poradi={poradi} sPristanim celkem={[["Celkem", motor]]} />
      </Blok>
    </>
  );
}
