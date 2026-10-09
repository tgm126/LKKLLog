import { useState } from "react";
import { useNavigate } from "react-router";

import { Hlaska } from "../komponenty/Hlaska";
import { Pole } from "../komponenty/Pole";
import { Stitek } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { proHledani } from "../text";
import "../komponenty/Volby.css";
import { rozdelitNazev, telefonCitelne, useOsoby, type Opravneni, type Osoba } from "./api";
import "./Osoby.css";

// Seznam osob pro správce osob (docs/modul-osoby.md, maketa osoby-mobil.html): hledání,
// filtr, řádek osoby s telefonem a štítky; ťuknutí otevře detail.

type Filtr = "aktivni" | "ucet" | "neaktivni" | "vse";

const FILTRY: [Filtr, string, (o: Osoba) => boolean][] = [
  ["aktivni", "Aktivní", (o) => o.platny],
  ["ucet", "S účtem", (o) => o.ucet !== null],
  ["neaktivni", "Neaktivní", (o) => !o.platny],
  ["vse", "Vše", () => true],
];

export function SeznamOsob() {
  const { data, error } = useOsoby();
  const navigate = useNavigate();
  const [hledat, setHledat] = useState("");
  const [filtr, setFiltr] = useState<Filtr>("aktivni");
  const dole = (
    <div className="dole">
      <Tlacitko varianta="modre" hlavni onClick={() => navigate("/osoba/nova")}>
        Nová osoba
      </Tlacitko>
    </div>
  );
  if (!data) {
    return (
      <>
        <main className="obsah">{error && <Hlaska>{error.message}</Hlaska>}</main>
        {dole}
      </>
    );
  }
  const h = proHledani(hledat.trim());
  // hledá v „jméno příjmení příjmení jméno e-mail telefon číslo“ (jméno v obou pořadích)
  const nalezene = data.osoby.filter(
    (o) =>
      !h ||
      proHledani(
        [o.jmeno, o.prijmeni, o.prijmeni, o.jmeno, o.email, o.telefon, o.cislo_clena].join(" "),
      ).includes(h),
  );
  const podle = FILTRY.find(([f]) => f === filtr)![2];
  return (
    <>
      <main className="obsah">
        <Pole
          popisek="Hledat jméno, e-mail, telefon, číslo člena"
          value={hledat}
          onChange={(e) => setHledat(e.target.value)}
        />
        <div className="segmenty filtr-osob">
          {FILTRY.map(([f, nazev, test]) => (
            <Tlacitko
              key={f}
              aria-pressed={filtr === f}
              onClick={() => setFiltr(f)}
            >
              {nazev} {f !== "vse" && <span className="cisla">{nalezene.filter(test).length}</span>}
            </Tlacitko>
          ))}
        </div>
        <div className="seznam-osob">
          {nalezene.filter(podle).map((o) => (
            <RadekOsoby
              key={o.id}
              osoba={o}
              opravneni={data.opravneni}
              otevrit={() => navigate(`/osoba/${o.id}`)}
            />
          ))}
        </div>
      </main>
      {dole}
    </>
  );
}

function RadekOsoby({
  osoba: o,
  opravneni,
  otevrit,
}: {
  osoba: Osoba;
  opravneni: Opravneni[];
  otevrit: () => void;
}) {
  type Stitky = [string, "modry" | "cerveny" | "pasek"][];
  const stitky: Stitky = [];
  if (o.ucet?.admin) stitky.push(["admin", "modry"]);
  else if (o.ucet?.spravuje_osoby) stitky.push(["správce osob", "modry"]);
  if (o.ucet?.zablokovano) stitky.push(["zablokován", "cerveny"]);
  if (!o.ucet) stitky.push(["bez účtu", "pasek"]);
  if (!o.clen) stitky.push(["externí", "pasek"]);
  for (const p of opravneni) {
    if (o.opravneni.some((x) => x.id === p.id)) stitky.push([rozdelitNazev(p.nazev)[0], "pasek"]);
  }
  return (
    <button
      type="button"
      className={o.platny ? "radek-osoby" : "radek-osoby neaktivni"}
      onClick={otevrit}
    >
      <span className="radek-osoby-jmeno">
        {o.prijmeni} {o.jmeno}
      </span>
      <span className="radek-osoby-telefon cisla">{telefonCitelne(o.telefon)}</span>
      {stitky.length > 0 && (
        <span className="radek-osoby-stitky">
          {stitky.map(([text, barva]) => (
            <Stitek key={text} barva={barva}>
              {text}
            </Stitek>
          ))}
        </span>
      )}
    </button>
  );
}
