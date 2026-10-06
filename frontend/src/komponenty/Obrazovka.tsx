import type { ReactNode } from "react";

import { Tlacitko } from "./Tlacitko";
import "./Obrazovka.css";

/** Obrazovka přes celý displej: ✕ / ← vlevo nahoře, nadpis, vpravo stav; akce dole. */
export function Obrazovka({
  zpet,
  zpetPopis,
  nadpis,
  vpravo,
  akce,
  children,
}: {
  zpet: () => void;
  /** „Zavřít“ (✕) nebo „Zpět“ (←) */
  zpetPopis: "Zavřít" | "Zpět";
  nadpis: ReactNode;
  vpravo?: ReactNode;
  akce?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="obrazovka">
      <div className="horni-lista">
        <Tlacitko varianta="bez-ramu" aria-label={zpetPopis} onClick={zpet}>
          {zpetPopis === "Zavřít" ? "✕" : "←"}
        </Tlacitko>
        <h1 className="velke tucne">{nadpis}</h1>
        {vpravo && <span className="horni-lista-vpravo">{vpravo}</span>}
      </div>
      <div className="obrazovka-obsah">{children}</div>
      {akce && <div className="obrazovka-akce">{akce}</div>}
    </section>
  );
}

export function Blok({ nadpis, children }: { nadpis: string; children: ReactNode }) {
  return (
    <div className="blok">
      <span className="nadpisek">{nadpis}</span>
      {children}
    </div>
  );
}
