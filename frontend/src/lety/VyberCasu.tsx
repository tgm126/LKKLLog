import { useState, type ReactNode } from "react";

import { Tlacitko } from "../komponenty/Tlacitko";
import "./Volby.css";

// Výběr času prstem bez psaní (maketa pruvodce-mobil-v4.html): pole vedle sebe (vzlet,
// přistání…), ťuknutí na pole → mřížka hodin → mřížka minut po pěti → doladění −1 / +1.
// Čas v minutách od půlnoci UTC zvoleného dne.

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

export type PoleCasu<K extends string> = { klic: K; nazev: string; min: number | null };

export function VolbaCasu<K extends string>({
  pole,
  aktivni,
  aktivovat,
  nastavit,
  limit,
  doplnek,
}: {
  pole: PoleCasu<K>[];
  /** Pole, které se právě vybírá (otevřená mřížka), nebo žádné. */
  aktivni: K | null;
  aktivovat: (klic: K | null) => void;
  /** Nová hodnota pole; vybrano = vybráno z mřížky (ne jen doladění ±1). */
  nastavit: (klic: K, min: number, vybrano: boolean) => void;
  /** Nejpozdější minuta, kterou jde vybrat (dnes nejde budoucnost). */
  limit: number;
  /** Mezi −1 a +1 (doba letu). */
  doplnek?: ReactNode;
}) {
  const [hodina, setHodina] = useState<number | null>(null);
  const min = pole.find((p) => p.klic === aktivni)?.min ?? null;
  return (
    <>
      <div className="casy-pole">
        {pole.map((p) => (
          <Tlacitko
            key={p.klic}
            className="cisla"
            aria-pressed={aktivni === p.klic}
            onClick={() => {
              setHodina(null);
              aktivovat(aktivni === p.klic ? null : p.klic);
            }}
          >
            <span>{p.nazev}</span> {p.min === null ? "—:—" : hhmm(p.min)}
          </Tlacitko>
        ))}
      </div>
      {aktivni !== null &&
        (hodina === null ? (
          <div className="mrizka-casu cisla">
            {Array.from({ length: 24 }, (_, h) => (
              <Tlacitko key={h} disabled={h * 60 > limit} onClick={() => setHodina(h)}>
                {dve(h)}
              </Tlacitko>
            ))}
          </div>
        ) : (
          <div className="mrizka-casu cisla">
            {Array.from({ length: 12 }, (_, k) => hodina * 60 + k * 5).map((m) => (
              <Tlacitko
                key={m}
                aria-pressed={m === min}
                disabled={m > limit}
                onClick={() => {
                  setHodina(null);
                  nastavit(aktivni, m, true);
                }}
              >
                {hhmm(m)}
              </Tlacitko>
            ))}
          </div>
        ))}
      {(aktivni !== null || doplnek) && (
        <div className="doladeni">
          <Tlacitko
            disabled={aktivni === null || min === null || min === 0}
            aria-label="o minutu dřív"
            onClick={() => nastavit(aktivni!, min! - 1, false)}
          >
            −1
          </Tlacitko>
          <span>{doplnek}</span>
          <Tlacitko
            disabled={aktivni === null || min === null || min >= limit}
            aria-label="o minutu později"
            onClick={() => nastavit(aktivni!, min! + 1, false)}
          >
            +1
          </Tlacitko>
        </div>
      )}
    </>
  );
}
