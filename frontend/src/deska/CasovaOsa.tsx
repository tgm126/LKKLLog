import { useState } from "react";
import { useNavigate } from "react-router";

import { hodinyMinuty, ted } from "../cas";
import { jakoTlacitko } from "../komponenty/klavesnice";
import { Blok } from "../komponenty/Obrazovka";
import type { Den, Pasek } from "../lety/api";
import { useSirokaDeska } from "../rozvrzeni";
import { useTik } from "../tik";

// Časová osa dne (docs/modul-desktop.md 3.5): řádek = letadlo, které ten den letělo,
// úsečka = let od vzletu do přistání (letící roste do „teď“). Rozsah podle dne – hodinu před
// začátkem občanského soumraku až hodinu po jeho konci, vždy i se všemi lety. Pásma soumraku
// (občanský, nautický, astronomický, noc) barevnou výplní. Kreslí se SVG s polohami
// v procentech – bez vložených stylů a pevných rozměrů.

const HODINA = 3_600_000;
const ms = (iso: string) => new Date(iso).getTime();

type Pasmo = { trida: string; od: number; do_: number; popis: string };

/** Pásma soumraku ráno a večer; chybějící čas (v létě astronomický) = pásmo až k okraji. */
function pasma(s: Den["slunce"], od: number, do_: number): Pasmo[] {
  const t = (iso: string | null) => (iso ? ms(iso) : null);
  const [ar, nr, tb, sr, ss, te, nv, av] = [t(s.ar), t(s.nr), t(s.tb), t(s.sr), t(s.ss), t(s.te), t(s.nv), t(s.av)];
  if (tb === null || sr === null || ss === null || te === null) return [];
  const p = (trida: string, popis: string, z: number | null, k: number | null): Pasmo[] =>
    z !== null && k !== null && k > z ? [{ trida, od: Math.max(z, od), do_: Math.min(k, do_), popis }] : [];
  return [
    ...p("noc", "noc", od, ar),
    ...p("astronomicky", "astronomický soumrak", ar ?? od, nr ?? od),
    ...p("nauticky", "nautický soumrak", nr ?? od, tb),
    ...p("obcansky", "občanský soumrak", tb, sr),
    ...p("obcansky", "občanský soumrak", ss, te),
    ...p("nauticky", "nautický soumrak", te, nv ?? do_),
    ...p("astronomicky", "astronomický soumrak", nv ?? do_, av ?? do_),
    ...p("noc", "noc", av, do_),
  ].filter((x) => x.do_ > x.od);
}

export function CasovaOsa({
  lety,
  den,
  poradi,
  vybranyId,
  dnes,
}: {
  lety: Pasek[];
  den: Den;
  /** Pořadí letadel (jako v řadě letadel). */
  poradi: string[];
  vybranyId: number | null;
  /** Dnešek: letící úsečky rostou a je vidět čára „teď“. */
  dnes: boolean;
}) {
  const siroka = useSirokaDeska();
  const [sbalena, setSbalena] = useState(!siroka);
  const navigate = useNavigate();
  useTik(); // letící úsečka roste, čára „teď“ se posouvá
  const nyni = ted().getTime();

  const letelo = lety.filter((l) => l.cas_vzletu && (l.stav === "UKONCEN" || l.stav === "VE_VZDUCHU"));
  const konec = (l: Pasek) => (l.cas_pristani ? ms(l.cas_pristani) : nyni);
  const poledne = ms(`${den.den}T12:00:00Z`);
  const od = Math.min(
    den.slunce.tb ? ms(den.slunce.tb) - HODINA : poledne - 6 * HODINA,
    ...letelo.map((l) => ms(l.cas_vzletu!)),
  );
  const do_ = Math.max(
    den.slunce.te ? ms(den.slunce.te) + HODINA : poledne + 6 * HODINA,
    ...letelo.map(konec),
  );
  const x = (t: number) => `${(((Math.min(Math.max(t, od), do_) - od) / (do_ - od)) * 100).toFixed(3)}%`;
  const sirka = (z: number, k: number) => `${Math.max(((k - z) / (do_ - od)) * 100, 0.35).toFixed(3)}%`;

  const hodiny: number[] = [];
  for (let h = Math.ceil(od / HODINA) * HODINA; h <= do_; h += HODINA) hodiny.push(h);
  const vrstva = pasma(den.slunce, od, do_);
  const letadla = [...new Set(letelo.map((l) => l.rejstrik))].sort(
    (a, b) => poradi.indexOf(a) - poradi.indexOf(b),
  );
  const pozadi = (
    <>
      {vrstva.map((p, i) => (
        <rect key={i} className={`osa-pasmo ${p.trida}`} x={x(p.od)} width={sirka(p.od, p.do_)} y="0" height="100%">
          <title>{`${p.popis} ${hodinyMinuty(new Date(p.od))}–${hodinyMinuty(new Date(p.do_))} UTC`}</title>
        </rect>
      ))}
      {hodiny.map((h) => (
        <line key={h} className="osa-hodina" x1={x(h)} x2={x(h)} y1="0" y2="100%" />
      ))}
      {dnes && <line className="osa-ted" x1={x(nyni)} x2={x(nyni)} y1="0" y2="100%" />}
    </>
  );

  return (
    <section className="casova-osa" aria-label="Časová osa dne">
      <Blok
        nadpis={
          <button type="button" className="osa-hlava" aria-expanded={!sbalena} onClick={() => setSbalena(!sbalena)}>
            {sbalena ? "▸" : "▾"} Časová osa dne
          </button>
        }
        vpravo={
          <span className="osa-legenda male seda">
            <span><i className="vzorek ukonceny" />ukončený</span>
            <span><i className="vzorek letici" />ve vzduchu</span>
            <span><i className="vzorek ted" />teď</span>
            <span>
              soumrak <i className="vzorek obcansky" />občanský <i className="vzorek nauticky" />nautický{" "}
              <i className="vzorek astronomicky" />astronomický <i className="vzorek noc" />noc
            </span>
            <span>· klik na let = detail</span>
          </span>
        }
      >
      {!sbalena && (
        <div className="osa-telo">
          <div className="osa-radek">
            <span />
            <svg className="osa-draha stupnice" aria-hidden>
              {hodiny.map((h) => (
                <text key={h} x={x(h)} y="75%" textAnchor="middle" className="osa-cislo">
                  {hodinyMinuty(new Date(h)).slice(0, 2)}
                </text>
              ))}
            </svg>
          </div>
          {letadla.map((r) => (
            <div key={r} className="osa-radek">
              <span className="male tucne">{r}</span>
              <svg className="osa-draha">
                {pozadi}
                {letelo
                  .filter((l) => l.rejstrik === r)
                  .map((l) => {
                    const z = ms(l.cas_vzletu!);
                    const trida = [
                      "osa-let",
                      l.stav === "VE_VZDUCHU" && (l.varovani ? "problem" : "letici"),
                      l.je_vlecny && "vlek",
                      l.id === vybranyId && "vybrany",
                    ];
                    const posadka = l.posadka.map((c) => `${c.jmeno} ${c.prijmeni}`).join(", ");
                    return (
                      <rect
                        key={l.id}
                        className={trida.filter(Boolean).join(" ")}
                        x={x(z)}
                        width={sirka(z, konec(l))}
                        y="20%"
                        height="60%"
                        rx="2"
                        aria-label={`Let ${l.rejstrik} ${hodinyMinuty(l.cas_vzletu!)}`}
                        {...jakoTlacitko(() => navigate(`/let/${l.id}`), "link")}
                      >
                        <title>
                          {`${l.rejstrik} ${hodinyMinuty(l.cas_vzletu!)}–${l.cas_pristani ? hodinyMinuty(l.cas_pristani) : "letí"} · ${posadka}`}
                        </title>
                      </rect>
                    );
                  })}
              </svg>
            </div>
          ))}
          {letadla.length === 0 && <p className="prazdny-sloupec male seda">Ten den zatím nikdo neletěl.</p>}
        </div>
      )}
      </Blok>
    </section>
  );
}
