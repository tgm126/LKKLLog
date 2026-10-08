import { type MouseEvent, type ReactNode } from "react";

import { doba, hodinyMinuty, stopky } from "../cas";
import { Stitek } from "../komponenty/Stitek";
import {
  Posadka,
  tridaPasku,
  ucelKratce,
  ulohaKratce,
  zpusobKratce,
  type LetPasku,
} from "../lety/Pasek";
import { useTik } from "../tik";
import "../lety/PanelLetu.css";
import "./PasekDeska.css";

// Pásek na desktopu (docs/modul-desktop.md 3.2, maketa provoz-desktop-v7.html): vodorovná
// řada přihrádek se svislými přepážkami jako papírový strip ŘLP – letadlo · posádka · štítky
// 2 × 2 v pevných pozicích (účel a způsob vzletu nahoře, POB a úloha dole) · trasa · čas ·
// akce. Stav letu říká jen výplň pásku; písmo v barvě textu (kromě varování a tlačítek).
// V panelu (detail, nový let) je pásek sám – prázdné přihrádky se vynechají.

/** Štítek na své pozici; bez údaje zůstane pozice prázdná (šířka i výška štítku). */
const pozice = (text: ReactNode, popis?: string | null) => (
  <span title={popis ?? undefined}>{text && <Stitek barva="pasek">{text}</Stitek>}</span>
);

/** Přihrádka času: stopky a vzlet / plán a kdy založen / vzlet–přistání a doba. */
function CasLetu({ let: l }: { let: LetPasku }) {
  const ted = useTik();
  if (l.stav === "VE_VZDUCHU" && l.cas_vzletu) {
    return (
      <>
        <span className="pasek-stopky">{stopky(l.cas_vzletu, ted)}</span>
        <span className="male seda">↑ {hodinyMinuty(l.cas_vzletu)}</span>
      </>
    );
  }
  if (l.stav === "UKONCEN" && l.cas_vzletu && l.cas_pristani) {
    return (
      <>
        <span>
          {hodinyMinuty(l.cas_vzletu)}–{hodinyMinuty(l.cas_pristani)}
        </span>
        <span>
          <b>{doba(l.doba_uctovana_min ?? 0)}</b>{" "}
          <span className="male seda">{l.pocet_pristani}×</span>
        </span>
      </>
    );
  }
  if (l.stav === "NAPLANOVAN") {
    return (
      <>
        <span className="male seda">plán</span>
        {l.zalozeno && <span className="male seda">zal. {hodinyMinuty(l.zalozeno)}</span>}
      </>
    );
  }
  return <span className="male seda">{l.stav === "ZRUSEN" ? "zrušen" : "nový let"}</span>;
}

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
  /** Pásek v panelu: bez prázdných přihrádek, nejde na něj kliknout. */
  vPanelu?: boolean;
  /** Obsah přihrádky času (jinak podle stavu letu). */
  cas?: ReactNode;
  onClick?: (e: MouseEvent) => void;
  /** Akce v přihrádce vpravo (T&G, PŘISTÁL, VZLET). */
  children?: ReactNode;
}) {
  const trasa = l.misto_vzletu || l.misto_pristani;
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
    <div className={trida.filter(Boolean).join(" ")} onClick={onClick}>
      <div className="prihradka">
        <span className="velke tucne">{l.rejstrik}</span>
        <span className="male seda">
          {l.typ}
          {l.je_vlecny && (
            <>
              {" · "}
              <b className="pasek-vlecna">vlečná</b>
            </>
          )}
        </span>
      </div>
      <div className="prihradka pasek-posadka">
        {l.posadka.length > 0 ? <Posadka clenove={l.posadka} /> : <span className="seda">— pilot —</span>}
      </div>
      <div className="prihradka pasek-stitky">
        {pozice(ucelKratce(l))}
        {pozice(zpusobKratce(l))}
        {pozice(l.pob !== null && `POB ${l.pob}`)}
        {pozice(ulohaKratce(l.uloha), l.uloha)}
      </div>
      {(trasa || !vPanelu) && (
        <div className="prihradka pasek-trasa">
          {trasa && (
            <>
              <span className="male">{misto(l.misto_vzletu)}</span>
              <span>→ {misto(l.misto_pristani)}</span>
            </>
          )}
        </div>
      )}
      <div className="prihradka pasek-cas cisla">{cas ?? <CasLetu let={l} />}</div>
      {(children || !vPanelu) && <div className="prihradka pasek-akce">{children}</div>}
      {l.varovani && <div className="pasek-varovani">{l.varovani}</div>}
    </div>
  );
}
