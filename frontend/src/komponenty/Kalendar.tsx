import { useState } from "react";

import { denSlovy, ted } from "../cas";
import { pocetLetu } from "../text";
import { Blok, BlokTelo } from "./Obrazovka";
import { Tlacitko } from "./Tlacitko";
import "./Kalendar.css";

// Kalendář letů po měsících (správa: smazat lety dne, export letů): dny s lety tučně s počtem
// letů, ostatní šedé a nejdou vybrat. Otevře se na měsíci posledního dne s lety.

const DNY_TYDNE = ["Po", "Út", "St", "Čt", "Pá", "So", "Ne"];

/** Měsíc RRRR-MM posunutý o `o` měsíců. */
export function posunMesice(mesic: string, o: number): string {
  const d = new Date(`${mesic}-01T12:00:00Z`);
  d.setUTCMonth(d.getUTCMonth() + o);
  return d.toISOString().slice(0, 7);
}

/** „říjen 2026“ z RRRR-MM. */
export const nazevMesice = (mesic: string) =>
  new Date(`${mesic}-01T12:00:00Z`).toLocaleDateString("cs-CZ", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });

export function Kalendar({
  dny,
  vybrat,
}: {
  dny: { den: string; lety: number }[];
  vybrat: (den: string) => void;
}) {
  const dnes = ted().toISOString().slice(0, 10);
  const lety = new Map(dny.map((d) => [d.den, d.lety]));
  const [mesic, setMesic] = useState((dny.at(-1)?.den ?? dnes).slice(0, 7));

  const prvni = new Date(`${mesic}-01T12:00:00Z`);
  const posun = (prvni.getUTCDay() + 6) % 7; // týden od pondělí
  const pocetDni = new Date(Date.UTC(prvni.getUTCFullYear(), prvni.getUTCMonth() + 1, 0)).getUTCDate();
  const dnyMesice = Array.from({ length: pocetDni }, (_, i) => `${mesic}-${String(i + 1).padStart(2, "0")}`);

  return (
    <Blok nadpis="Kalendář letů" vpravo="tučně = dny s lety" popis="Kalendář letů">
      <BlokTelo>
        <div className="kalendar-mesic">
          <Tlacitko varianta="bez-ramu" aria-label="Předchozí měsíc" onClick={() => setMesic(posunMesice(mesic, -1))}>
            ‹
          </Tlacitko>
          <span className="velke tucne">{nazevMesice(mesic)}</span>
          <Tlacitko varianta="bez-ramu" aria-label="Další měsíc" onClick={() => setMesic(posunMesice(mesic, 1))}>
            ›
          </Tlacitko>
        </div>
        <div className="kalendar">
          {DNY_TYDNE.map((d) => (
            <span key={d} className="kalendar-den-tydne male seda">
              {d}
            </span>
          ))}
          {Array.from({ length: posun }, (_, i) => (
            <span key={`prazdny-${i}`} />
          ))}
          {dnyMesice.map((den) => {
            const n = lety.get(den);
            return (
              <button
                key={den}
                type="button"
                className={["kalendar-den", n && "s-lety", den === dnes && "dnes"].filter(Boolean).join(" ")}
                disabled={!n}
                aria-label={n ? `${denSlovy(den)} – ${pocetLetu(n)}` : denSlovy(den)}
                onClick={() => vybrat(den)}
              >
                <span className="cisla">{Number(den.slice(8))}</span>
                <span className="kalendar-pocet male cisla">{n ?? "\u00a0"}</span>
              </button>
            );
          })}
        </div>
      </BlokTelo>
    </Blok>
  );
}
