import type { ReactNode } from "react";
import { useLocation, useNavigate } from "react-router";

import { Tlacitko } from "./Tlacitko";
import "./Obrazovka.css";

/** Zpět tam, odkud uživatel přišel (nabídka uživatele, štítek v hlavičce); otevřeno přímo
 *  adresou = na přehled. */
export function useZpet() {
  const navigate = useNavigate();
  const odkud = useLocation();
  return () => (odkud.key === "default" ? navigate("/") : navigate(-1));
}

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
          <Tlacitko varianta="bez-ramu" className="zpet" aria-label={zpetPopis} onClick={zpet}>
            <svg className="ikona" viewBox="0 0 24 24" aria-hidden>
              {zpetPopis === "Zavřít" ? (
                <path d="M6 6l12 12M18 6L6 18" />
              ) : (
                <path d="M20 12H5M11 5l-7 7 7 7" />
              )}
            </svg>
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
  popis,
  roztazeny = false,
  children,
}: {
  nadpis: ReactNode;
  vpravo?: ReactNode;
  /** Název oblasti pro čtečky a testy (karty desky). */
  popis?: string;
  /** Vyplní výšku sloupce, obsah se posouvá uvnitř (deník dne na desce). */
  roztazeny?: boolean;
  children: ReactNode;
}) {
  return (
    <section className={roztazeny ? "blok karta roztazeny" : "blok karta"} aria-label={popis}>
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
