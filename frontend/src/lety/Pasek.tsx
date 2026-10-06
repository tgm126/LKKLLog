import { Fragment, type MouseEvent, type ReactNode } from "react";
import { useNavigate } from "react-router";

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

/** Odchylky od běžného letu: účel, způsob vzletu, vlek. Ve dvojici (kluzák + vlečná na
 *  jednom pásku) je vlek vidět – štítek „vlek“ se vynechá. */
function odchylky(l: PasekLetu, veDvojici = false): string[] {
  return [
    l.ucel && l.ucel_kod !== "NORMALNI" ? malymi(l.ucel) : "",
    l.zpusob_vzletu_kod !== "VLASTNI" ? malymi(l.zpusob_vzletu) : "",
    l.je_vlecny && !veDvojici ? "vlek" : "",
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
/** Ťuknutí na pásek otevře detail letu (tlačítka akcí ne). */
function useOtevrit(letId: number) {
  const navigate = useNavigate();
  return (e: MouseEvent) => {
    if (!(e.target as HTMLElement).closest("button")) navigate(`/let/${letId}`);
  };
}

/** Polovina dvojitého pásku (kluzák / vlečná) – ťuknutí otevře detail svého letu. */
function Polovina({ letId, children }: { letId: number; children: ReactNode }) {
  return (
    <div className="let-par" onClick={useOtevrit(letId)}>
      {children}
    </div>
  );
}

/** Akce z pásku: provést (letId, akce); zaneprázdněn = akce tohoto letu právě běží. */
type AkcePasku = { provest: (letId: number, akce: Akce) => void; zaneprazdnen: boolean };

const misto = (kod: string | null, cas: string | null) =>
  [kod, cas && hodinyMinuty(cas)].filter(Boolean).join(" ");

/** Let ve vzduchu; vlek jako dvojitý pásek, dokud jsou ve vzduchu kluzák i vlečná
 *  (každý má své stopky a PŘISTÁL). */
export function PasekVeVzduchu({ lety, provest, zaneprazdnen }: { lety: PasekLetu[] } & AkcePasku) {
  const ted = useTik();
  const veDvojici = lety.length > 1;
  return (
    <div className={`let ${lety.some((l) => l.varovani) ? "problem" : "vzduch"}`}>
      {lety.map((l) => (
        <Polovina key={l.id} letId={l.id}>
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
              ...odchylky(l, veDvojici).map((o) => <Stitek key={o}>{o}</Stitek>),
            ]}
          </Stitky>
          {l.varovani && <div className="let-duvod">{l.varovani}</div>}
          <div className="let-akce">
            {/* T&G jen motorová letadla, TMG a UL; počet přímo na tlačítku */}
            {l.kategorie_kod !== "KLUZAK" && (
              <Tlacitko
                varianta="svetle"
                disabled={zaneprazdnen}
                onClick={() => provest(l.id, "tg")}
              >
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
        </Polovina>
      ))}
    </div>
  );
}

/** Naplánovaný let; vlek jako dvojitý pásek (kluzák a vlečná startují společně). */
export function PasekNaplanovany({
  lety,
  provest,
  zaneprazdnen,
}: { lety: PasekLetu[] } & AkcePasku) {
  const veDvojici = lety.length > 1;
  return (
    <div className="let naplanovan">
      <div className="let-vedle">
        <div>
      {lety.map((l) => {
        const udaje = [
          l.pob ? `POB ${l.pob}` : "",
          l.misto_vzletu ? `z ${l.misto_vzletu}` : "",
          ...odchylky(l, veDvojici),
        ].filter(Boolean);
        return (
          <Polovina key={l.id} letId={l.id}>
            <div className="let-radek">
              <span className="velke tucne">{l.rejstrik}</span>
              <span className="let-typ">{typ(l)}</span>
            </div>
            <div className="let-radek">
              <Posadka clenove={l.posadka} />
            </div>
            <Stitky>{udaje.map((u) => <Stitek key={u}>{u}</Stitek>)}</Stitky>
          </Polovina>
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
  const otevrit = useOtevrit(l.id);
  return (
    <div className="let ukoncen" onClick={otevrit}>
      <div className="let-radek">
        <b>{l.rejstrik}</b>
        <Posadka clenove={l.posadka} />
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
  const otevrit = useOtevrit(l.id);
  return (
    <div className="let zrusen" onClick={otevrit}>
      <div className="let-radek">
        <b>{l.rejstrik}</b>
        <Posadka clenove={pic(l)} />
        <span className="let-vpravo male">{l.duvod_zruseni}</span>
      </div>
    </div>
  );
}
