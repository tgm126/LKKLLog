import type { ReactNode } from "react";

import { Tlacitko } from "./Tlacitko";
import "./Obrazovka.css";

/** Obrazovka přes celý displej: ✕ / ← vlevo nahoře, nadpis, vpravo stav; akce dole. */
export function Obrazovka({
  zpet,
  zpetPopis,
  nadpis,
  vpravo,
  pod,
  akce,
  children,
}: {
  zpet: () => void;
  /** „Zavřít“ (✕) nebo „Zpět“ (←) */
  zpetPopis: "Zavřít" | "Zpět";
  nadpis: ReactNode;
  vpravo?: ReactNode;
  /** Pod horní lištou přes celou šířku (ukazatel postupu průvodce). */
  pod?: ReactNode;
  akce?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="obrazovka">
      <div className="horni-lista">
        <div className="horni-lista-radek">
          <Tlacitko varianta="bez-ramu" aria-label={zpetPopis} onClick={zpet}>
            {zpetPopis === "Zavřít" ? "✕" : "←"}
          </Tlacitko>
          <h1 className="velke tucne">{nadpis}</h1>
          {vpravo && <span className="horni-lista-vpravo">{vpravo}</span>}
        </div>
        {pod}
      </div>
      <div className="obrazovka-obsah">{children}</div>
      {akce && <div className="obrazovka-akce">{akce}</div>}
    </section>
  );
}

/** Blok obrazovky: karta s hlavičkou (nadpis, vpravo doplněk). */
export function Blok({
  nadpis,
  vpravo,
  children,
}: {
  nadpis: ReactNode;
  vpravo?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="blok">
      <h2 className="blok-nadpis nadpisek">
        {nadpis}
        {vpravo && <span className="blok-vpravo">{vpravo}</span>}
      </h2>
      {children}
    </section>
  );
}

/** Tělo bloku s odsazením (volby, seznamy). */
export function BlokTelo({ children }: { children: ReactNode }) {
  return <div className="blok-telo">{children}</div>;
}
