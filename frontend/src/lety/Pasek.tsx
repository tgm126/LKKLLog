import { Fragment } from "react";

import { doba, hodinyMinuty, stopky } from "../cas";
import { Stitek, Stitky } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useTik } from "../tik";
import type { Akce } from "./akce";
import type { Clen, Pasek as PasekLetu } from "./api";
import "./Pasek.css";

// Pásky podle makety docs/navrhy/lety-mobil.html: běžný případ je tichý, štítky jen při
// odchylce (účel ≠ normální, naviják / vlek, místo ≠ domovské).

const malymi = (text: string) => text.toLocaleLowerCase("cs-CZ");

/** Odchylky od běžného letu: účel, způsob vzletu, vlečení. */
function odchylky(l: PasekLetu): string[] {
  return [
    l.ucel && l.ucel_kod !== "NORMALNI" ? malymi(l.ucel) : "",
    l.zpusob_vzletu_kod !== "VLASTNI" ? malymi(l.zpusob_vzletu) : "",
    l.je_vlecny && l.vlek_rejstrik ? `vleče ${l.vlek_rejstrik}` : "",
  ].filter(Boolean);
}

function Posadka({ clenove }: { clenove: Clen[] }) {
  return clenove.map((c) => (
    <Fragment key={c.funkce_kod}>
      <span>
        {c.jmeno} {c.prijmeni}
      </span>
      <span className="funkce">{c.funkce_kod === "PIC" ? "PIC" : malymi(c.funkce)}</span>
    </Fragment>
  ));
}

const pic = (l: PasekLetu) => l.posadka.filter((c) => c.funkce_kod === "PIC");
const typ = (l: PasekLetu) => (l.je_vlecny ? `${l.typ} · vlečná` : l.typ);
/** Akce z pásku: provést (letId, akce); zaneprázdněn = akce tohoto letu právě běží. */
type AkcePasku = { provest: (letId: number, akce: Akce) => void; zaneprazdnen: boolean };

const misto = (kod: string | null, cas: string | null) =>
  [kod, cas && hodinyMinuty(cas)].filter(Boolean).join(" ");

export function PasekVeVzduchu({ let: l, provest, zaneprazdnen }: { let: PasekLetu } & AkcePasku) {
  const ted = useTik();
  return (
    <div className={`let ${l.varovani ? "problem" : "vzduch"}`}>
      <div className="let-radek">
        <span className="velke tucne">{l.rejstrik}</span>
        <span className="let-typ">{typ(l)}</span>
        <span className="let-vpravo let-cas cisla">
          {l.cas_vzletu && stopky(l.cas_vzletu, ted)}
        </span>
      </div>
      <div className="let-radek">
        <Posadka clenove={l.posadka} />
      </div>
      <Stitky>
        {[
          <Stitek key="vzlet">vzlet {misto(l.misto_vzletu, l.cas_vzletu)}</Stitek>,
          l.pob && <Stitek key="pob">POB {l.pob}</Stitek>,
          ...odchylky(l).map((o) => <Stitek key={o}>{o}</Stitek>),
        ]}
      </Stitky>
      {l.varovani && <div className="let-duvod">{l.varovani}</div>}
      <div className="let-akce">
        {/* T&G jen motorová letadla, TMG a UL; počet přímo na tlačítku */}
        {l.kategorie_kod !== "KLUZAK" && (
          <Tlacitko varianta="svetle" disabled={zaneprazdnen} onClick={() => provest(l.id, "tg")}>
            T&amp;G <span className="cisla">{l.pocet_tg}</span>
          </Tlacitko>
        )}
        <Tlacitko
          varianta="zelene"
          hlavni
          disabled={zaneprazdnen}
          onClick={() => provest(l.id, "pristani")}
        >
          Přistál
        </Tlacitko>
      </div>
    </div>
  );
}

/** Naplánovaný let; vlek jako dvojitý pásek (kluzák a vlečná startují společně). */
export function PasekNaplanovany({
  lety,
  provest,
  zaneprazdnen,
}: { lety: PasekLetu[] } & AkcePasku) {
  const vlek = lety.length > 1;
  return (
    <div className="let naplanovan">
      <div className="let-vedle">
        <div>
      {lety.map((l) => {
        const udaje = [
          l.pob ? `POB ${l.pob}` : "",
          l.misto_vzletu ? `z ${l.misto_vzletu}` : "",
          // Ve dvojici je vidět, koho vlečná vleče – štítek „vleče“ by se opakoval.
          ...odchylky(l).filter((o) => !(vlek && o.startsWith("vleče"))),
        ].filter(Boolean);
        return (
          <div key={l.id} className="let-par">
            <div className="let-radek">
              <span className="velke tucne">{l.rejstrik}</span>
              <span className="let-typ">{typ(l)}</span>
            </div>
            <div className="let-radek">
              <Posadka clenove={l.posadka} />
              {udaje.length > 0 && <span className="funkce">· {udaje.join(" · ")}</span>}
            </div>
          </div>
        );
      })}
        </div>
        {/* U vleku jeden VZLET pro oba lety */}
        <Tlacitko
          varianta="modre"
          hlavni
          disabled={zaneprazdnen}
          onClick={() => provest(lety[0]!.id, "vzlet")}
        >
          Vzlet
        </Tlacitko>
      </div>
    </div>
  );
}

export function PasekUkonceny({ let: l }: { let: PasekLetu }) {
  return (
    <div className="let ukoncen">
      <div className="let-radek">
        <b>{l.rejstrik}</b>
        <Posadka clenove={pic(l)} />
        <span className="let-vpravo tucne cisla">{doba(l.doba_uctovana_min ?? 0)}</span>
      </div>
      <Stitky>
        {[
          <Stitek key="casy">
            {misto(l.misto_vzletu, l.cas_vzletu)} → {misto(l.misto_pristani, l.cas_pristani)}
          </Stitek>,
          l.pob && <Stitek key="pob">POB {l.pob}</Stitek>,
          (l.pocet_pristani ?? 1) > 1 && (
            <Stitek key="pristani">{l.pocet_pristani} přistání</Stitek>
          ),
          ...odchylky(l).map((o) => <Stitek key={o}>{o}</Stitek>),
          l.dodatecne && <Stitek key="dodatecne">dodatečně</Stitek>,
        ]}
      </Stitky>
    </div>
  );
}

export function PasekZruseny({ let: l }: { let: PasekLetu }) {
  return (
    <div className="let zrusen">
      <div className="let-radek">
        <b>{l.rejstrik}</b>
        <Posadka clenove={pic(l)} />
        <span className="let-vpravo male">{l.duvod_zruseni}</span>
      </div>
    </div>
  );
}
