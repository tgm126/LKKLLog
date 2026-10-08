import { type MouseEvent, type ReactNode } from "react";

import { doba, hodinyMinuty, stopky } from "../cas";
import { Sipka } from "../komponenty/Sipka";
import { Posadka, StitkyPasku, tridaPasku, type LetPasku } from "../lety/Pasek";
import { useTik } from "../tik";
import "../lety/PanelLetu.css";
import "./PasekDeska.css";

// Pásek na desktopu (docs/modul-desktop.md 3.2): vodorovná řada přihrádek jako papírový
// strip ŘLP (bez svislých přepážek) – letadlo · posádka · čas, vpravo akce; pod nimi řádek
// štítků v pevných pozicích (jako na mobilu) a pod časem vždy trasa odkud → kam (i moje
// letiště, šedě – na desktopu je místo; rozhodnuto 8. 10. 2026). Stav letu říká jen
// výplň pásku; písmo v barvě textu (kromě varování a tlačítek). V panelu (detail, nový let)
// je pásek sám – bez akcí nezabírá místo pro tlačítka.

/** Přihrádka času: stopky a vzlet / plán a kdy založen / vzlet–přistání a doba. */
function CasLetu({ let: l }: { let: LetPasku }) {
  const ted = useTik();
  if (l.stav === "VE_VZDUCHU" && l.cas_vzletu) {
    return (
      <>
        <span className="pasek-stopky">{stopky(l.cas_vzletu, ted)}</span>
        <span className="male seda">
          <Sipka smer="vzlet" /> {hodinyMinuty(l.cas_vzletu)}
        </span>
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
  /** Pásek v panelu: bez prázdné přihrádky akcí, nejde na něj kliknout. */
  vPanelu?: boolean;
  /** Obsah přihrádky času (jinak podle stavu letu). */
  cas?: ReactNode;
  onClick?: (e: MouseEvent) => void;
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
      <div className="prihradka pasek-cas cisla">{cas ?? <CasLetu let={l} />}</div>
      {(children || !vPanelu) && <div className="pasek-akce">{children}</div>}
      <StitkyPasku
        let={l}
        trasa={
          <>
            {misto(l.misto_vzletu)} <Sipka smer="kam" /> {misto(l.misto_pristani)}
          </>
        }
      />
      {l.varovani && <div className="pasek-varovani">{l.varovani}</div>}
    </div>
  );
}
