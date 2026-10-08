import { type MouseEvent, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { doba, hodinyMinuty, stopky } from "../cas";
import { Stitek } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useTik } from "../tik";
import { useJenCteni } from "../uzivatel";
import type { Akce, LetKPristani } from "./akce";
import type { Pasek as PasekLetu, Stav } from "./api";
import "./Pasek.css";

// Pásky letů podle maket docs/navrhy/lety-mobil-v4.html a pasek-mobil-v5.html.
// Ve vzduchu a naplánované: barevný panel s výrazným okrajem jako papírový strip – rejstřík
// a typ · posádka (každá osoba na vlastním řádku) · vpravo čas · dole štítky v pevných
// pozicích (účel · způsob vzletu · POB · úloha); chybí-li údaj, místo zůstane prázdné.
// U ukončeného letu vpravo v řádku štítků doba a počet přistání. Stejný pásek je nahoře
// v detailu letu a rozpracovaný v průvodci. Ukončené a zrušené: deník – řádky v jedné kartě
// (letadlo · posádka · čas · doba · přistání).

const malymi = (text: string) => text.toLocaleLowerCase("cs-CZ");
/** „Vlastní (motorem)“ → „vlastní“ – v poli pásku jen krátce. */
const kratce = (text: string) => malymi(text.replace(/\s*\(.*\)\s*/, ""));
/** Krátké názvy účelů, aby se vešly do pole (jinak název z číselníku). */
const UCEL_KRATCE: Record<string, string> = { VYCVIK_SOLO: "sólo", PREZKOUSENI: "přezk." };

/** Údaje pásku – přehled letů (Pasek), detail letu i rozpracovaný let v průvodci. */
export type LetPasku = Pick<
  PasekLetu,
  | "rejstrik"
  | "typ"
  | "je_vlecny"
  | "ucel"
  | "ucel_kod"
  | "zpusob_vzletu"
  | "zpusob_vzletu_kod"
  | "cas_vzletu"
  | "cas_pristani"
  | "doba_uctovana_min"
  | "pocet_pristani"
  | "uloha"
  | "varovani"
> & {
  stav: Stav | "ROZPRACOVANY";
  pob: number | null;
  posadka: { jmeno: string; prijmeni: string; funkce: string; funkce_kod: string }[];
  /** Místa jen tehdy, když nejsou moje letiště (server je u pásků vynechá). */
  misto_vzletu?: string | null;
  misto_pristani?: string | null;
  /** Kdy byl let založen (desktop: u naplánovaného letu v přihrádce času). */
  zalozeno?: string;
};

/** Trasa na pásek (maketa mista-letu-mobil.html, varianta B): jen jedna strana – kam letí
 *  („→ LKMB“), jinak odkud („LKMB →“); jen naplánovaný let a let ve vzduchu. */
function trasa(l: LetPasku): string | null {
  if (l.stav !== "VE_VZDUCHU" && l.stav !== "NAPLANOVAN") return null;
  if (l.misto_pristani) return `→ ${l.misto_pristani}`;
  return l.misto_vzletu ? `${l.misto_vzletu} →` : null;
}

/** Účel do pole pásku; běžný (normální) se nevypisuje, vlečná má „vlek“. */
export function ucelKratce(l: LetPasku) {
  if (l.je_vlecny) return "vlek";
  if (!l.ucel_kod || l.ucel_kod === "NORMALNI") return null;
  return UCEL_KRATCE[l.ucel_kod] ?? (l.ucel && malymi(l.ucel));
}

/** Způsob vzletu do pole pásku; vlastní (motorem) se nevypisuje. */
export const zpusobKratce = (l: LetPasku) =>
  l.zpusob_vzletu_kod && l.zpusob_vzletu_kod !== "VLASTNI" ? kratce(l.zpusob_vzletu) : null;

/** Označení úlohy (IU/4) z názvu „IU/4 Navijákové vzlety…“. */
export const ulohaKratce = (uloha: string | null) => uloha?.split(" ")[0] ?? null;

/** Posádka: každá osoba na vlastním řádku, funkce malým šedým písmem. */
export function Posadka({ clenove }: { clenove: LetPasku["posadka"] }) {
  return clenove.map((c) => (
    <span key={c.funkce_kod}>
      {c.jmeno} {c.prijmeni}{" "}
      <span className="funkce">{c.funkce_kod === "PIC" ? "PIC" : malymi(c.funkce)}</span>
    </span>
  ));
}

/** Štítek na své pozici; bez údaje zůstane pozice prázdná. */
const pozice = (text: ReactNode) => <span>{text && <Stitek barva="pasek">{text}</Stitek>}</span>;

/** Přihrádka času vpravo podle stavu: stopky a vzlet / vzlet nad přistáním / plán. */
function CasLetu({ let: l }: { let: LetPasku }) {
  const ted = useTik();
  if (l.stav === "VE_VZDUCHU" && l.cas_vzletu) {
    return (
      <>
        <span className="let-stopky">{stopky(l.cas_vzletu, ted)}</span>
        <span className="male seda">↑ {hodinyMinuty(l.cas_vzletu)}</span>
      </>
    );
  }
  if (l.cas_vzletu) {
    return (
      <>
        <b>{hodinyMinuty(l.cas_vzletu)}</b>
        <span className="seda">{l.cas_pristani ? hodinyMinuty(l.cas_pristani) : "—:—"}</span>
      </>
    );
  }
  return <span className="male seda">{l.stav === "ZRUSEN" ? "zrušen" : "plán"}</span>;
}

/** Jedna polovina pásku (u vleku kluzák a vlečná pod sebou): přihrádky a pás údajů. */
export function PolovinaPasku({
  let: l,
  cas,
  onClick,
  children,
}: {
  let: LetPasku;
  /** Obsah přihrádky času (jinak podle stavu letu). */
  cas?: ReactNode;
  onClick?: (e: MouseEvent) => void;
  /** Akce pod páskem (PŘISTÁL, T&G). */
  children?: ReactNode;
}) {
  const ukoncen = l.stav === "UKONCEN";
  const kam = trasa(l);
  return (
    <div className={onClick ? "let-par otevira" : "let-par"} onClick={onClick}>
      <div className="let-hlava">
        <span className="velke tucne">{l.rejstrik}</span>
        <span className="let-typ">
          {l.typ}
          {l.je_vlecny && (
            <>
              {" · "}
              <b>vlečná</b>
            </>
          )}
        </span>
      </div>
      <div className="let-posadka">
        <Posadka clenove={l.posadka} />
      </div>
      <div className="let-cas cisla">{cas ?? <CasLetu let={l} />}</div>
      <div className="stitky-pasku">
        {pozice(ucelKratce(l))}
        {pozice(zpusobKratce(l))}
        {pozice(l.pob !== null && `POB ${l.pob}`)}
        {pozice(ulohaKratce(l.uloha))}
        {kam && (
          <span className="trasa-pasku">
            <Stitek barva="pasek" zkratit>
              {kam}
            </Stitek>
          </span>
        )}
        {ukoncen && (
          <b className="vysledek-letu cisla">
            {doba(l.doba_uctovana_min ?? 0)}
            <span className="pocet-pristani">{l.pocet_pristani}×</span>
          </b>
        )}
      </div>
      {l.varovani && <div className="let-varovani">{l.varovani}</div>}
      {children && <div className="let-akce">{children}</div>}
    </div>
  );
}

/** Třída pásku podle stavu (barevný panel). */
export const tridaPasku = (lety: LetPasku[]) =>
  lety.some((l) => l.varovani)
    ? "problem"
    : ({
        VE_VZDUCHU: "vzduch",
        NAPLANOVAN: "naplanovan",
        UKONCEN: "ukoncen",
        ZRUSEN: "zrusen",
        ROZPRACOVANY: "rozpracovany",
      } as const)[lety[0]!.stav];

/** Ťuknutí na pásek otevře detail letu (tlačítka akcí ne). */
function useOtevrit(letId: number) {
  const navigate = useNavigate();
  return (e: MouseEvent) => {
    if (!(e.target as HTMLElement).closest("button")) navigate(`/let/${letId}`);
  };
}

/** Polovina pásku v přehledu – ťuknutí otevře detail svého letu. */
function Polovina({ let: l, children }: { let: PasekLetu; children?: ReactNode }) {
  return (
    <PolovinaPasku let={l} onClick={useOtevrit(l.id)}>
      {children}
    </PolovinaPasku>
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
  const jenCteni = useJenCteni();
  return (
    <div className={`let ${tridaPasku(lety)}`}>
      {lety.map((l) => (
        <Polovina key={l.id} let={l}>
          {/* T&G jen motorová letadla, TMG a UL, ne vlečná (při vleku nedělá); počet na tlačítku */}
          {!jenCteni && l.kategorie_kod !== "KLUZAK" && !l.je_vlecny && (
            <Tlacitko varianta="obrys" disabled={zaneprazdnen} onClick={() => provest(l.id, "tg")}>
              T&amp;G <span className="cisla">{l.pocet_tg}</span>
            </Tlacitko>
          )}
          {!jenCteni && (
            <Tlacitko varianta="zelene" hlavni disabled={zaneprazdnen} onClick={() => pristat(l)}>
              Přistál
            </Tlacitko>
          )}
        </Polovina>
      ))}
    </div>
  );
}

/** Naplánovaný let; vlek jako dvojitý pásek (kluzák a vlečná startují společně). */
export function PasekNaplanovany({ lety, provest, zaneprazdnen }: { lety: PasekLetu[] } & AkcePasku) {
  const jenCteni = useJenCteni();
  return (
    <div className="let naplanovan">
      {lety.map((l) => (
        <Polovina key={l.id} let={l} />
      ))}
      {/* VZLET pod páskem přes celou šířku (jako PŘISTÁL); u vleku jeden pro oba lety */}
      {!jenCteni && (
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
      )}
    </div>
  );
}

// --- deník: ukončené a zrušené lety --------------------------------------------------------

/** Podrobnosti do třetího řádku: vždy POB, pak odchylky od běžného letu (účel, způsob
 *  vzletu, úloha, dodatečně). */
function podrobnosti(l: PasekLetu) {
  return [
    `POB ${l.pob}`,
    ucelKratce(l),
    zpusobKratce(l),
    ulohaKratce(l.uloha),
    l.dodatecne && "dodatečně",
  ].filter(Boolean);
}

function RadekDeniku({ let: l }: { let: PasekLetu }) {
  const otevrit = useOtevrit(l.id);
  const zrusen = l.stav === "ZRUSEN";
  // Dva řádky pro posádku (druhý prázdný, je-li osoba jen jedna), třetí řádek podrobnosti.
  const [prvni, ...dalsi] = (
    zrusen ? l.posadka.filter((c) => c.funkce_kod === "PIC") : l.posadka
  ).map((c) => `${c.jmeno} ${c.prijmeni}`);
  const doplnek = zrusen ? [l.duvod_zruseni] : podrobnosti(l);
  return (
    <div className={`denik-radek ${zrusen ? "zrusen" : "ukoncen"}`} onClick={otevrit}>
      <span className="denik-rejstrik">{l.rejstrik}</span>
      <span className="denik-posadka">
        <span>{prvni}</span>
        <span>{dalsi.join(" · ") || " "}</span>
      </span>
      <span className="denik-cas cisla">
        {l.cas_vzletu && <span>{hodinyMinuty(l.cas_vzletu)}</span>}
        {l.cas_pristani && <span className="seda">{hodinyMinuty(l.cas_pristani)}</span>}
      </span>
      <span className="denik-doba cisla">{!zrusen && doba(l.doba_uctovana_min ?? 0)}</span>
      <span className="denik-pristani cisla">{!zrusen && l.pocet_pristani}</span>
      {doplnek.length > 0 && (
        <span className="denik-podrobnosti male seda">{doplnek.join(" · ")}</span>
      )}
    </div>
  );
}

/** Ukončené (nebo zrušené – bez záhlaví) lety jako deník v jedné kartě. */
export function Denik({ lety, zahlavi = true }: { lety: PasekLetu[]; zahlavi?: boolean }) {
  return (
    <div className="denik">
      {zahlavi && (
        <div className="denik-radek zahlavi" aria-hidden>
          <span>Letadlo</span>
          <span>Posádka</span>
          <span className="denik-cas">Čas</span>
          <span className="denik-doba">Doba</span>
          <span className="denik-pristani">P</span>
        </div>
      )}
      {lety.map((l) => (
        <RadekDeniku key={l.id} let={l} />
      ))}
    </div>
  );
}
