import type { MouseEvent, ReactNode } from "react";

import { Tlacitko } from "./Tlacitko";
import "./Obrazovka.css";
import "./Panel.css";

/** Po kliknutí v obsahu panelu (otevřená volba, Hledat…, úprava údaje) se blok posune tak,
 *  aby byl celý vidět – nic se neotevře pod spodním okrajem. Volá se po vykreslení změny. */
function ukazatBlok(e: MouseEvent) {
  const blok = (e.target as Element).closest(".blok");
  requestAnimationFrame(() => blok?.scrollIntoView({ block: "nearest", behavior: "smooth" }));
}

/** Desktop: panel zprava přes desku (detail letu, nový let) – nahoře hlava a zavírací
 *  křížek, uprostřed posuvný obsah, dole akce. Deska pod ním zůstává ovladatelná. */
export function Panel({
  nadpis,
  hlava,
  siroky = false,
  zavrit,
  pata,
  children,
}: {
  /** Popis pro čtečky a testy (např. „Detail letu“). */
  nadpis: string;
  hlava: ReactNode;
  /** Širší panel (formulář nového letu ve dvou sloupcích). */
  siroky?: boolean;
  zavrit: () => void;
  pata?: ReactNode;
  children: ReactNode;
}) {
  return (
    <aside className={siroky ? "panel siroky" : "panel"} aria-label={nadpis}>
      <div className="panel-hlava">
        <div className="panel-hlava-obsah">{hlava}</div>
        <Tlacitko varianta="bez-ramu" className="panel-zavrit" aria-label="Zavřít (Esc)" title="Zavřít (Esc)" onClick={zavrit}>
          <svg className="ikona" viewBox="0 0 24 24" aria-hidden>
            <path d="M6 6l12 12M18 6L6 18" />
          </svg>
        </Tlacitko>
      </div>
      <div className="panel-telo" onClick={ukazatBlok}>
        {children}
      </div>
      {pata && <div className="panel-pata">{pata}</div>}
    </aside>
  );
}
