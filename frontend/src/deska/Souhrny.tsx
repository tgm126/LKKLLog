import { doba } from "../cas";
import type { Pasek } from "../lety/api";

// Souhrny dne v pravém sloupci (docs/modul-desktop.md 3.4): plachtařský provoz (kluzáky
// a vleky) a motorový provoz (vše ostatní, i TMG a vlastní lety vlečné mimo vlek). Nahoře
// P (počet přistání), doba letů (a doba vleků), pod tím letadla s dobou a P. Jen ukončené
// lety; počítá se z letů dne, nic se neukládá.

const minut = (lety: Pasek[]) => lety.reduce((s, l) => s + (l.doba_uctovana_min ?? 0), 0);
const pristani = (lety: Pasek[]) => lety.reduce((s, l) => s + (l.pocet_pristani ?? 0), 0);

function Letadla({ lety, poradi }: { lety: Pasek[]; poradi: string[] }) {
  const radky = [...new Set(lety.map((l) => `${l.rejstrik}|${l.je_vlecny}`))]
    .map((klic) => {
      const [rejstrik, vlecny] = klic.split("|");
      return { rejstrik: rejstrik!, vleky: vlecny === "true", lety: lety.filter((l) => `${l.rejstrik}|${l.je_vlecny}` === klic) };
    })
    .sort((a, b) => poradi.indexOf(a.rejstrik) - poradi.indexOf(b.rejstrik));
  if (radky.length === 0) return null;
  return (
    <table className="tabulka-souhrnu cisla">
      <thead>
        <tr>
          <th>Letadlo</th>
          <th>Doba</th>
          <th title="Počet přistání">P</th>
        </tr>
      </thead>
      <tbody>
        {radky.map((r) => (
          <tr key={`${r.rejstrik}${r.vleky}`}>
            <td>
              <b>{r.rejstrik}</b>
              {r.vleky && <span className="male seda"> vleky</span>}
            </td>
            <td>
              <b>{doba(minut(r.lety))}</b>
            </td>
            <td>{pristani(r.lety)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Cislo({ hodnota, popis, titulek }: { hodnota: string | number; popis: string; titulek?: string }) {
  return (
    <div title={titulek}>
      <b className="velke cisla">{hodnota}</b>
      <span className="male seda">{popis}</span>
    </div>
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
        <div className="cisla-souhrnu">
          <Cislo hodnota={pristani(kluzaky)} popis="P" titulek="Počet přistání kluzáků" />
          <Cislo hodnota={doba(minut(kluzaky))} popis="doba letů" />
          <Cislo hodnota={doba(minut(vleky))} popis="doba vleků" />
        </div>
        <Letadla lety={[...kluzaky, ...vleky]} poradi={poradi} />
      </section>
      <section className="karta-souhrnu" aria-label="Motorový provoz">
        <h2 className="nadpisek">Motorový provoz</h2>
        <div className="cisla-souhrnu">
          <Cislo hodnota={pristani(motor)} popis="P" titulek="Počet přistání" />
          <Cislo hodnota={doba(minut(motor))} popis="doba letů" />
        </div>
        <Letadla lety={motor} poradi={poradi} />
      </section>
    </>
  );
}
