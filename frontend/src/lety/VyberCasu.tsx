import { useState } from "react";

import { Blok } from "../komponenty/Obrazovka";
import { Tlacitko } from "../komponenty/Tlacitko";
import "./Volby.css";

// Výběr času prstem bez psaní (maketa lety-mobil.html): ťuknutí na pole → mřížka hodin →
// mřížka minut po pěti → doladění −1 / +1. Čas v minutách od půlnoci UTC zvoleného dne.

const dve = (n: number) => String(n).padStart(2, "0");
export const hhmm = (min: number) => `${dve(Math.floor(min / 60))}:${dve(min % 60)}`;

/** Začátek dne (UTC) v ms a převody minut na ISO čas a místní čas. */
export function denUtc(zacatekDneMs: number) {
  const datum = (min: number) => new Date(zacatekDneMs + min * 60_000);
  return {
    iso: (min: number) => datum(min).toISOString(),
    mistni: (min: number) =>
      datum(min).toLocaleTimeString("cs-CZ", {
        timeZone: "Europe/Prague",
        hour: "2-digit",
        minute: "2-digit",
      }),
  };
}

/** Minuty od půlnoci UTC */
export const minutyUtc = (cas: string | Date) => {
  const d = new Date(cas);
  return d.getUTCHours() * 60 + d.getUTCMinutes();
};

export function VyberCasu({
  nadpis,
  min,
  otevreno,
  prepnout,
  nastavit,
  limit,
  mistni,
}: {
  nadpis: string;
  min: number | null;
  otevreno: boolean;
  prepnout: () => void;
  /** Nová hodnota; vybrano = vybráno z mřížky (ne jen doladění ±1). */
  nastavit: (min: number, vybrano: boolean) => void;
  /** Nejpozdější minuta, kterou jde vybrat (dnes nejde budoucnost). */
  limit: number;
  mistni: (min: number) => string;
}) {
  const [hodina, setHodina] = useState<number | null>(null);
  return (
    <Blok nadpis={`${nadpis} (UTC)${min === null ? "" : ` · místní ${mistni(min)}`}`}>
      <div className="cas-pole">
        <Tlacitko
          varianta="obrys"
          className="krok"
          disabled={min === null || min === 0}
          aria-label="o minutu dřív"
          onClick={() => nastavit(min! - 1, false)}
        >
          −1
        </Tlacitko>
        <Tlacitko
          varianta="obrys"
          className="hodnota cisla"
          aria-pressed={otevreno}
          onClick={() => {
            setHodina(null);
            prepnout();
          }}
        >
          {min === null ? "—:—" : hhmm(min)}
        </Tlacitko>
        <Tlacitko
          varianta="obrys"
          className="krok"
          disabled={min === null || min >= limit}
          aria-label="o minutu později"
          onClick={() => nastavit(min! + 1, false)}
        >
          +1
        </Tlacitko>
      </div>
      {otevreno &&
        (hodina === null ? (
          <div className="mrizka-casu">
            {Array.from({ length: 24 }, (_, h) => (
              <Tlacitko
                key={h}
                varianta="obrys"
                className="cisla"
                disabled={h * 60 > limit}
                onClick={() => setHodina(h)}
              >
                {dve(h)}
              </Tlacitko>
            ))}
          </div>
        ) : (
          <div className="mrizka-casu minuty">
            {Array.from({ length: 12 }, (_, k) => hodina * 60 + k * 5).map((m) => (
              <Tlacitko
                key={m}
                varianta="obrys"
                className="cisla"
                disabled={m > limit}
                onClick={() => {
                  setHodina(null);
                  nastavit(m, true);
                }}
              >
                {hhmm(m)}
              </Tlacitko>
            ))}
          </div>
        ))}
    </Blok>
  );
}
