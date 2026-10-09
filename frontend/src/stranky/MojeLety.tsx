import { useRef } from "react";
import { useSearchParams } from "react-router";

import { denSlovy } from "../cas";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useDen, useLety, useMojeDny } from "../lety/api";
import { PrehledLetu } from "./Lety";
import "./MojeLety.css";

/** Moje lety (telefon, docs/modul-moje-lety.md): lety jednoho dne, kde jsem v posádce –
 *  stejně jako v Lety (pásky s akcemi, deník); ťuknutí otevře detail. Den v adrese (?den=),
 *  aby Zpět z detailu vrátil na stejný den; šipky skáčou po dnech s mými lety, ťuknutí na
 *  datum otevře kalendář telefonu. */
export function MojeLety() {
  const [hledani, setHledani] = useSearchParams();
  const den = hledani.get("den") ?? undefined;
  const dnes = useDen().data?.den;
  const dny = useMojeDny().data ?? [];
  const { data: lety, error, dataUpdatedAt } = useLety(den, true);
  const kalendar = useRef<HTMLInputElement>(null);

  const aktualni = den ?? dnes;
  const zmenit = (d: string) => setHledani(d === dnes ? {} : { den: d }, { replace: true });
  const predchozi = aktualni ? dny.filter((d) => d < aktualni).at(-1) : undefined;
  // dopředu: další den s mými lety, jinak dnešek (do budoucnosti ne)
  const dalsi =
    aktualni && dnes && aktualni < dnes
      ? (dny.find((d) => d > aktualni && d <= dnes) ?? dnes)
      : undefined;

  const vyberDne = (
    <div className="vyber-dne">
      <Tlacitko
        varianta="obrys"
        aria-label="Předchozí den s mými lety"
        disabled={!predchozi}
        onClick={() => predchozi && zmenit(predchozi)}
      >
        ‹
      </Tlacitko>
      <Tlacitko
        varianta="bez-ramu"
        className="vyber-dne-datum"
        onClick={() => kalendar.current?.showPicker()}
      >
        {aktualni ? denSlovy(aktualni) : "…"}
        {aktualni === dnes && <span className="seda"> · dnes</span>}
      </Tlacitko>
      <input
        ref={kalendar}
        type="date"
        aria-label="Vybrat den"
        className="vyber-dne-kalendar"
        max={dnes}
        value={aktualni ?? ""}
        onChange={(e) => e.target.value && zmenit(e.target.value)}
      />
      <Tlacitko
        varianta="obrys"
        aria-label="Další den s mými lety"
        disabled={!dalsi}
        onClick={() => dalsi && zmenit(dalsi)}
      >
        ›
      </Tlacitko>
    </div>
  );

  return (
    <PrehledLetu
      lety={lety}
      error={error}
      dataUpdatedAt={dataUpdatedAt}
      prazdne="V tento den nemáte žádný let."
      nahore={vyberDne}
    />
  );
}
