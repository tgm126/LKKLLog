import { Fragment, type MouseEvent, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { doba, hodinyMinuty, stopky } from "../cas";
import { Stitek, Stitky } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useTik } from "../tik";
import type { Akce, LetKPristani } from "./akce";
import { useDen, type Clen, type Pasek as PasekLetu } from "./api";
import "./Pasek.css";

// Pásky podle makety docs/navrhy/lety-mobil.html. Pod posádkou řádek údajů v pevných
// sloupcích (stejný údaj vždy na stejném místě, i když chybí):
//   1 čas (a letiště, není-li domovské) · 2 účel · 3 způsob vzletu · 4 POB · 5 úloha;
// pod nimi doplňky jen s rámečkem (počet přistání, dodatečně).

const malymi = (text: string) => text.toLocaleLowerCase("cs-CZ");
/** „Vlastní (motorem)“ → „vlastní“ – na štítku jen krátce. */
const kratce = (text: string) => malymi(text.replace(/\s*\(.*\)\s*/, ""));
/** Krátké názvy účelů, aby se vešly do sloupce (jinak název z číselníku). */
const UCEL_KRATCE: Record<string, string> = { VYCVIK_SOLO: "sólo", PREZKOUSENI: "přezk." };

const misto = (kod: string | null, cas: string | null) =>
  [kod, cas && hodinyMinuty(cas)].filter(Boolean).join(" ");

function UdajeLetu({ let: l }: { let: PasekLetu }) {
  const domovske = useDen().data?.domovske ?? null;
  const cas =
    l.stav === "NAPLANOVAN"
      ? (l.misto_vzletu ?? domovske)
      : l.stav === "VE_VZDUCHU"
        ? misto(l.misto_vzletu, l.cas_vzletu)
        : `${misto(l.misto_vzletu, l.cas_vzletu)} → ${misto(l.misto_pristani, l.cas_pristani)}`;
  const ucel = l.je_vlecny
    ? "vlek"
    : l.ucel_kod && (UCEL_KRATCE[l.ucel_kod] ?? (l.ucel && malymi(l.ucel)));
  const sloupce = [cas, ucel, kratce(l.zpusob_vzletu), `POB ${l.pob}`, l.uloha?.split(" ")[0]];
  const doplnky = [
    (l.pocet_pristani ?? 1) > 1 && `${l.pocet_pristani} přistání`,
    l.dodatecne && "dodatečně",
  ].filter((d): d is string => !!d);
  return (
    <>
      <div className="udaje">
        {sloupce.map((u, i) => (
          <span key={i}>{u && <Stitek>{u}</Stitek>}</span>
        ))}
      </div>
      {doplnky.length > 0 && (
        <Stitky>
          {doplnky.map((d) => (
            <Stitek key={d} barva="obrys">
              {d}
            </Stitek>
          ))}
        </Stitky>
      )}
    </>
  );
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
type AkcePasku = {
  provest: (letId: number, akce: Akce) => void;
  /** PŘISTÁL – u letu kratšího než minuta se nejdřív zeptá. */
  pristat: (l: LetKPristani) => void;
  zaneprazdnen: boolean;
};


/** Let ve vzduchu; vlek jako dvojitý pásek, dokud jsou ve vzduchu kluzák i vlečná
 *  (každý má své stopky a PŘISTÁL). */
export function PasekVeVzduchu({
  lety,
  provest,
  pristat,
  zaneprazdnen,
}: { lety: PasekLetu[] } & AkcePasku) {
  const ted = useTik();
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
          <UdajeLetu let={l} />
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
              onClick={() => pristat(l)}
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
  return (
    <div className="let naplanovan">
      {lety.map((l) => (
        <Polovina key={l.id} letId={l.id}>
          <div className="let-radek">
            <span className="velke tucne">{l.rejstrik}</span>
            <span className="let-typ">{typ(l)}</span>
          </div>
          <div className="let-radek">
            <Posadka clenove={l.posadka} />
          </div>
          <UdajeLetu let={l} />
        </Polovina>
      ))}
      {/* VZLET pod páskem přes celou šířku (jako PŘISTÁL); u vleku jeden pro oba lety */}
      <div className="let-akce">
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
      <UdajeLetu let={l} />
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
