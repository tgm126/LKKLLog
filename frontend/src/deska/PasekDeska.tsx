import type { ReactNode } from "react";

import { jakoTlacitko, type Klik } from "../komponenty/klavesnice";
import { Sipka } from "../komponenty/Sipka";
import { CasLetu, Letadlo, Posadka, StitkyPasku, tridaPasku, Varovani, type LetPasku } from "../lety/Pasek";
import "../lety/PanelLetu.css";
import "./PasekDeska.css";

// Pásek na desktopu (docs/modul-desktop.md 3.2): vodorovná řada přihrádek jako papírový
// strip ŘLP (bez svislých přepážek) – letadlo · posádka · čas, vpravo akce; pod nimi řádek
// štítků v pevných pozicích (jako na mobilu) a pod časem vždy trasa odkud → kam (i moje
// letiště, šedě – na desktopu je místo; rozhodnuto 8. 10. 2026). Stav letu říká jen
// výplň pásku; písmo v barvě textu (kromě varování a tlačítek). V panelu (detail, nový let)
// je pásek sám – bez akcí nezabírá místo pro tlačítka.

export function PasekDeska({
  let: l,
  mojeKod,
  vybrany = false,
  vPanelu = false,
  cas,
  onClick,
  children,
}: {
  let: LetPasku;
  /** Moje letiště – v trase šedě (server ho u pásků vynechá, doplní se zpět). */
  mojeKod: string | undefined;
  /** Otevřený v detailu – výrazný prstenec. */
  vybrany?: boolean;
  /** Pásek v panelu: bez prázdné přihrádky akcí, nejde na něj kliknout. */
  vPanelu?: boolean;
  /** Obsah přihrádky času (jinak podle stavu letu). */
  cas?: ReactNode;
  onClick?: Klik;
  /** Akce v přihrádce vpravo (T&G, PŘISTÁL, VZLET). */
  children?: ReactNode;
}) {
  const misto = (kod: string | null | undefined) =>
    kod ? <b>{kod}</b> : <span className="seda">{mojeKod}</span>;
  const trida = [
    "pasek-deska",
    "panel-letu",
    tridaPasku([l]),
    vPanelu && "v-panelu",
    vybrany && "vybrany",
    onClick && "otevira",
  ];
  return (
    <div className={trida.filter(Boolean).join(" ")} {...jakoTlacitko(onClick, "link")}>
      <div className="prihradka">
        <Letadlo let={l} />
      </div>
      <div className="prihradka pasek-posadka">
        {l.posadka.length > 0 ? <Posadka clenove={l.posadka} /> : <span className="seda">— pilot —</span>}
      </div>
      <div className="prihradka pasek-cas cisla">{cas ?? <CasLetu let={l} deska />}</div>
      {(children || !vPanelu) && <div className="pasek-akce">{children}</div>}
      <StitkyPasku
        let={l}
        trasa={
          <>
            {misto(l.misto_vzletu)} <Sipka smer="kam" /> {misto(l.misto_pristani)}
          </>
        }
      />
      <Varovani let={l} />
    </div>
  );
}
