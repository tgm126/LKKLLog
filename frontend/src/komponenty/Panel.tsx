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

/** Desktop: panel zprava přes desku (detail letu, nový let) – nahoře hlava (pásek letu
 *  přes celou šířku), uprostřed posuvný obsah, dole akce a vpravo Zavřít (i klávesa Esc).
 *  Deska pod ním zůstává ovladatelná. */
export function Panel({
  nadpis,
  hlava,
  siroky = false,
  cely = false,
  zavrit,
  pata,
  children,
}: {
  /** Popis pro čtečky a testy (např. „Detail letu“). */
  nadpis: string;
  hlava: ReactNode;
  /** Širší panel (formulář nového letu ve dvou sloupcích). */
  siroky?: boolean;
  /** Panel přes celou desku (editor výcviku). */
  cely?: boolean;
  zavrit: () => void;
  pata?: ReactNode;
  children: ReactNode;
}) {
  return (
    <aside className={["panel", siroky && "siroky", cely && "cely"].filter(Boolean).join(" ")} aria-label={nadpis}>
      <div className="panel-hlava">{hlava}</div>
      <div className="panel-telo" onClick={ukazatBlok}>
        {children}
      </div>
      <div className="panel-pata">
        <div className="panel-akce">{pata}</div>
        <Tlacitko varianta="obrys" title="Zavřít (Esc)" onClick={zavrit}>
          Zavřít
        </Tlacitko>
      </div>
    </aside>
  );
}
