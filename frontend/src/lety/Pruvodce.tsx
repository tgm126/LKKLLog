import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate } from "react-router";

import { poslat } from "../api";
import { doba, hodinyMinuty, stopky, ted } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, Obrazovka } from "../komponenty/Obrazovka";
import { useOznamit } from "../komponenty/Oznameni";
import { Stitek, Stitky } from "../komponenty/Stitek";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useJa } from "../uzivatel";
import { oznamitAkci, type Provedeno } from "./akce";
import {
  useNabidky,
  type LetadloNabidka,
  type Nabidky,
  type Osoba,
  type Ucel,
  type Uloha,
} from "./api";
import "./Pruvodce.css";
import "./Volby.css";
import { denUtc, minutyUtc, VyberCasu } from "./VyberCasu";
import { VolbaMista, type Misto } from "./VyberMista";

// Průvodce novým letem podle makety docs/navrhy/lety-mobil.html:
// 1 letadlo → 2 posádka → 3 let (úloha, u kluzáku vzlet a vlek, plátce) → VZLET TEĎ /
// Naplánovat / Proběhlý let (výběr časů prstem).

/** Popisek PIC podle účelu (kdo je velitel letadla). */
export const PIC_NAZEV: Record<string, string> = {
  VYCVIK: "Instruktor (PIC)",
  VYCVIK_SOLO: "Žák (PIC)",
  PREZKOUSENI: "Examinátor (PIC)",
};

type Novy = {
  letadlo?: LetadloNabidka;
  ucelId?: number;
  /** funkce_id → osoba_id */
  osoby: Record<number, number>;
  pob: number;
  zpusob?: "NAVIJAK" | "VLEK";
  vlecna?: LetadloNabidka;
  vlekar?: number;
  uloha?: number;
  platce?: number | "aeroklub";
  /** prázdné = domovské letiště */
  mistoVzletu?: Misto;
};

type Krok = 1 | 2 | 3 | "casy";

export const jmeno = (o: Osoba) => `${o.jmeno} ${o.prijmeni}`;

export function Pruvodce() {
  const { data: nabidky, error } = useNabidky();
  const navigate = useNavigate();
  const zavrit = () => navigate("/", { replace: true });
  if (!nabidky) {
    return (
      <Obrazovka zpet={zavrit} zpetPopis="Zavřít" nadpis="Nový let">
        {error && <Hlaska>{error.message}</Hlaska>}
      </Obrazovka>
    );
  }
  return <PruvodceKroky nabidky={nabidky} zavrit={zavrit} />;
}

function PruvodceKroky({ nabidky, zavrit }: { nabidky: Nabidky; zavrit: () => void }) {
  const ja = useJa().data!;
  const [krok, setKrok] = useState<Krok>(1);
  const [novy, setNovy] = useState<Novy>({ osoby: {}, pob: 1 });
  const [rozbaleno, setRozbaleno] = useState<string | null>(null);
  const zmenit = (zmena: Partial<Novy>) => {
    setNovy((n) => ({ ...n, ...zmena }));
    setRozbaleno(null);
  };

  const letadlo = novy.letadlo;
  // Jen účely, u kterých se posádka na palubě (PIC + žák / přezkoušený) vejde do letadla –
  // u jednomístného normální let a sólo (dozor je na zemi).
  const ucelyPro = (a: LetadloNabidka | undefined) =>
    nabidky.ucely.filter(
      (u) => !a || 1 + u.funkce.filter((f) => f.na_palube).length <= a.pocet_mist,
    );
  const ucely = ucelyPro(letadlo);
  const ucel: Ucel =
    ucely.find((u) => u.id === novy.ucelId) ??
    ucely.find((u) => u.kod === "NORMALNI") ??
    ucely[0]!;
  const kluzak = letadlo?.kategorie_kod === "KLUZAK";
  const aerovlek = kluzak && novy.zpusob === "VLEK";
  const osoba = (id: number | undefined) => nabidky.osoby.find((o) => o.id === id);

  // Pole posádky podle účelu: PIC + funkce, které účel vyžaduje (žák, dozor, přezkoušený).
  const pole = [
    { funkceId: nabidky.pic_id, nazev: PIC_NAZEV[ucel.kod] ?? "PIC" },
    ...ucel.funkce.map((f) => ({ funkceId: f.id, nazev: f.nazev })),
  ];
  const posadkaHotova = pole.every((p) => novy.osoby[p.funkceId]);

  // Výchozí plátce: kdo je na palubě s jinou funkcí než PIC (žák, přezkoušený), jinak PIC.
  const naPalube = ucel.funkce.find((f) => f.na_palube && novy.osoby[f.id]);
  const vychoziPlatce = novy.osoby[naPalube?.id ?? nabidky.pic_id];
  const platce = novy.platce ?? vychoziPlatce;

  const zpet = () => {
    setRozbaleno(null);
    if (krok === 1) zavrit();
    else setKrok(krok === "casy" ? 3 : ((krok - 1) as Krok));
  };
  const nadpisKroku: Record<Krok, string> = {
    1: "1 / 3 · Letadlo",
    2: "2 / 3 · Posádka",
    3: "3 / 3 · Let",
    casy: "Proběhlý let",
  };
  const spolecne = {
    trida: "pruvodce",
    zpet,
    zpetPopis: krok === 1 ? ("Zavřít" as const) : ("Zpět" as const),
    nadpis: krok === 1 || !letadlo ? "Nový let" : letadlo.rejstrik,
    vpravo: <span className="nadpisek">{nadpisKroku[krok]}</span>,
  };

  // --- krok 1: letadlo -----------------------------------------------------------------------
  if (krok === 1 || !letadlo) {
    return (
      <Obrazovka {...spolecne}>
        <div className="dlazdice-mrizka">
          {nabidky.letadla.map((a) => (
            <Dlazdice
              key={a.id}
              letadlo={a}
              vybrana={a.id === letadlo?.id}
              vybrat={() => {
                // účel, který se do letadla nevejde, se vrátí na normální (zůstane jen PIC)
                const ucelSedi = ucelyPro(a).some((u) => u.id === novy.ucelId);
                zmenit({
                  letadlo: a,
                  ...(ucelSedi
                    ? {}
                    : {
                        ucelId: undefined,
                        osoby: Object.fromEntries(
                          Object.entries(novy.osoby).filter(([f]) => Number(f) === nabidky.pic_id),
                        ),
                        platce: undefined,
                      }),
                  pob: Math.min(novy.pob, a.pocet_mist),
                  zpusob: novy.zpusob ?? (nabidky.zpusob_kluzaku === "VLEK" ? "VLEK" : "NAVIJAK"),
                  uloha: undefined,
                });
                setKrok(2);
              }}
            />
          ))}
        </div>
      </Obrazovka>
    );
  }

  // Osoba: rychlá volba (Já, nedávní / vlekaři, Všichni…); vybraná je modře jako ostatní
  // volby v průvodci, ťuknutím na jinou se změní. Stejná osoba nemůže mít dvě funkce.
  const obsazene = (krome: string) =>
    [
      ...pole.filter((p) => `f${p.funkceId}` !== krome).map((p) => novy.osoby[p.funkceId]),
      krome === "vlekar" ? undefined : aerovlek ? novy.vlekar : undefined,
    ].filter(Boolean);
  const volbaOsoby = (
    klic: string,
    nazev: string,
    vybrana: number | undefined,
    rychle: number[],
    vybrat: (id: number | undefined) => void,
  ) => {
    const vsichni = rozbaleno === klic;
    const nabidka = (
      vsichni
        ? nabidky.osoby
        : [...new Set([...rychle, ...(vybrana ? [vybrana] : [])])]
            .map(osoba)
            .filter((o): o is Osoba => o !== undefined)
    ).filter((o) => !obsazene(klic).includes(o.id));
    return (
      <Blok key={klic} nadpis={nazev}>
        <div className="navrhy">
          {nabidka.map((o) => (
            <Tlacitko
              key={o.id}
              varianta="obrys"
              aria-pressed={o.id === vybrana}
              onClick={() => vybrat(o.id)}
            >
              {o.id === ja.osoba_id ? `Já (${jmeno(o)})` : jmeno(o)}
            </Tlacitko>
          ))}
          {!vsichni && (
            <Tlacitko varianta="bez-ramu" onClick={() => setRozbaleno(klic)}>
              Všichni…
            </Tlacitko>
          )}
        </div>
      </Blok>
    );
  };

  // --- krok 2: posádka -----------------------------------------------------------------------
  if (krok === 2) {
    const pob = ucel.funkce.length === 0 && letadlo.pocet_mist > 1;
    return (
      <Obrazovka
        {...spolecne}
        akce={
          <Tlacitko
            varianta="modre"
            hlavni
            disabled={!posadkaHotova}
            onClick={() => {
              setRozbaleno(null);
              setKrok(3);
            }}
          >
            Dál
          </Tlacitko>
        }
      >
        <Blok nadpis="Účel">
          <div className="volby">
            {ucely.map((u) => (
              <Tlacitko
                key={u.id}
                varianta="obrys"
                aria-pressed={u.id === ucel.id}
                onClick={() =>
                  zmenit({
                    ucelId: u.id,
                    // PIC zůstane, ostatní funkce závisí na účelu
                    osoby: Object.fromEntries(
                      Object.entries(novy.osoby).filter(([f]) => Number(f) === nabidky.pic_id),
                    ),
                    uloha: undefined,
                    platce: undefined,
                  })
                }
              >
                {u.nazev}
              </Tlacitko>
            ))}
          </div>
        </Blok>
        {pole.map((p) =>
          volbaOsoby(
            `f${p.funkceId}`,
            p.nazev,
            novy.osoby[p.funkceId],
            [ja.osoba_id, ...letadlo.nedavni],
            (id) => {
              const osoby = { ...novy.osoby };
              if (id) osoby[p.funkceId] = id;
              else delete osoby[p.funkceId];
              zmenit({ osoby, platce: undefined });
            },
          ),
        )}
        {pob && (
          <Blok nadpis="POB">
            <VolbaPoctu
              pocet={letadlo.pocet_mist}
              vybrano={novy.pob}
              vybrat={(n) => zmenit({ pob: n })}
            />
          </Blok>
        )}
      </Obrazovka>
    );
  }

  // --- krok 3: let a proběhlý let ------------------------------------------------------------
  const ulohy = nabidky.ulohy.filter(
    (u) =>
      u.ucel_id === ucel.id && (u.kategorie_kod === null || u.kategorie_kod === letadlo.kategorie_kod),
  );
  // Úloha je povinná podle účelu, ale jen když pro účel a kategorii letadla nějaká existuje
  // (stejné pravidlo hlídá databáze).
  const ulohaPovinna = ucel.uloha_povinna && ulohy.length > 0;
  const hotovo =
    posadkaHotova &&
    (!ulohaPovinna || novy.uloha !== undefined) &&
    (!aerovlek || (novy.vlecna !== undefined && novy.vlekar !== undefined));
  const muzeVzlet = !letadlo.leti_od && !(aerovlek && novy.vlecna?.leti_od);
  const vlecne = nabidky.letadla.filter((a) => a.vlecne && !a.mimo_provoz);

  const props = {
    nabidky,
    novy,
    ucel,
    letadlo,
    aerovlek,
    platce,
    zavrit,
  };

  if (krok === "casy") {
    return <ProbehlyLet {...props} spolecne={spolecne} />;
  }

  return (
    <Obrazovka
      {...spolecne}
      akce={
        <Dokonceni
          {...props}
          hotovo={hotovo}
          muzeVzlet={muzeVzlet}
          probehly={() => setKrok("casy")}
        />
      }
    >
      {kluzak && (
        <Blok nadpis="Způsob vzletu">
          <div className="volby">
            {(["NAVIJAK", "VLEK"] as const).map((z) => (
              <Tlacitko
                key={z}
                varianta="obrys"
                aria-pressed={novy.zpusob === z}
                onClick={() => zmenit({ zpusob: z })}
              >
                {nabidky.zpusoby.find((zp) => zp.kod === z)?.nazev}
              </Tlacitko>
            ))}
          </div>
        </Blok>
      )}
      {aerovlek && (
        <>
          <Blok nadpis="Vlečná">
            <div className="dlazdice-mrizka">
              {vlecne.map((a) => (
                <Dlazdice
                  key={a.id}
                  letadlo={a}
                  vybrana={a.id === novy.vlecna?.id}
                  vybrat={() => {
                    // vlekař posledního vleku – jen když není v posádce kluzáku
                    const posledni = a.posledni_vlekar ?? undefined;
                    const vPosadce = Object.values(novy.osoby).includes(posledni ?? -1);
                    zmenit({ vlecna: a, vlekar: novy.vlekar ?? (vPosadce ? undefined : posledni) });
                  }}
                />
              ))}
            </div>
          </Blok>
          {volbaOsoby(
            "vlekar",
            "Vlekař",
            novy.vlekar,
            nabidky.osoby.filter((o) => o.vlekar).map((o) => o.id),
            (id) => zmenit({ vlekar: id }),
          )}
        </>
      )}
      <VolbaUlohy
        key={ucel.id}
        ulohy={ulohy}
        povinna={ulohaPovinna}
        vybrana={ulohy.find((u) => u.id === novy.uloha)}
        vybrat={(id) => zmenit({ uloha: id })}
      />
      <Blok nadpis="Místo vzletu">
        <VolbaMista
          nabidky={nabidky}
          misto={novy.mistoVzletu}
          zmenit={(m) => zmenit({ mistoVzletu: m })}
        />
      </Blok>
      <Blok nadpis="Platí">
        {/* Předvyplněný podle účelu (modře); jiná osoba z posádky, Aeroklub, nebo kdokoli. */}
        <div className="navrhy">
          {[
            ...new Set([
              ...pole.map((p) => novy.osoby[p.funkceId]).filter((id): id is number => !!id),
              "aeroklub" as const,
              ...(typeof platce === "number" ? [platce] : []),
              ...(rozbaleno === "platce" ? nabidky.osoby.map((o) => o.id) : []),
            ]),
          ].map((id) => (
            <Tlacitko
              key={id}
              varianta="obrys"
              aria-pressed={id === platce}
              onClick={() => zmenit({ platce: id })}
            >
              {id === "aeroklub" ? "Aeroklub" : jmeno(osoba(id)!)}
            </Tlacitko>
          ))}
          {rozbaleno !== "platce" && (
            <Tlacitko varianta="bez-ramu" onClick={() => setRozbaleno("platce")}>
              Všichni…
            </Tlacitko>
          )}
        </div>
      </Blok>
    </Obrazovka>
  );
}

// --- dlaždice letadla ------------------------------------------------------------------------

function Dlazdice({
  letadlo: a,
  vybrana,
  vybrat,
}: {
  letadlo: LetadloNabidka;
  vybrana: boolean;
  vybrat: () => void;
}) {
  const trida = ["dlazdice", a.mimo_provoz ? "mimo" : a.leti_od ? "leti" : "", vybrana && "vybrana"];
  return (
    <button
      type="button"
      className={trida.filter(Boolean).join(" ")}
      disabled={a.mimo_provoz}
      aria-pressed={vybrana}
      onClick={vybrat}
    >
      <span className="dlazdice-rejstrik">{a.rejstrik}</span>
      <span className="male seda">{a.typ}</span>
      <span className="male seda">{a.kategorie}</span>
      <Stitky>
        {[
          a.leti_od && (
            <Stitek key="leti" barva="zeleny">
              letí {stopky(a.leti_od, ted()).slice(0, -3)}
            </Stitek>
          ),
          a.naplanovan && <Stitek key="plan">naplánován</Stitek>,
          a.mimo_provoz && (
            <Stitek key="mimo" barva="oranzovy">
              mimo provoz
            </Stitek>
          ),
          a.vlecne && <Stitek key="vlecne">vlečná</Stitek>,
          a.soukrome && <Stitek key="soukrome">soukromé</Stitek>,
        ]}
      </Stitky>
    </button>
  );
}

// --- úloha ---------------------------------------------------------------------------------

/** Úloha ve dvou krocích: osnova (IU, IA, II…), pak úloha v ní (vzestupně podle osnovy).
 *  Co je vybrané, zůstane samo (ostatní se skryjí); ťuknutím na vybrané se nabídka znovu
 *  otevře, změní se až výběrem jiné. Je-li úloha povinná a osnova jen jedna, je rovnou
 *  otevřená. Nepovinnou úlohu jde zrušit volbou „Bez úlohy“. */
export function VolbaUlohy({
  ulohy,
  povinna,
  vybrana,
  vybrat,
  menit = false,
}: {
  ulohy: Uloha[];
  povinna: boolean;
  vybrana: Uloha | undefined;
  vybrat: (id: number | undefined) => void;
  /** Rovnou nabídka úloh vybrané osnovy (úprava v detailu letu). */
  menit?: boolean;
}) {
  const osnovy = [...new Map(ulohy.map((u) => [u.osnova_id, u.osnova])).entries()];
  const [osnovaId, setOsnovaId] = useState<number | undefined>(
    vybrana?.osnova_id ?? (povinna && osnovy.length === 1 ? osnovy[0]![0] : undefined),
  );
  // Která nabídka je otevřená: výběr osnovy, výběr úlohy v osnově, nebo žádná (vybráno).
  const [otevreno, setOtevreno] = useState<"osnova" | "uloha" | null>(
    vybrana && !menit ? null : osnovaId === undefined ? "osnova" : "uloha",
  );
  if (ulohy.length === 0) return null;
  const osnova = osnovy.find(([id]) => id === osnovaId);
  const vybrat_ = (id: number | undefined) => {
    vybrat(id);
    setOtevreno(null);
  };
  return (
    <Blok nadpis={povinna ? "Úloha" : "Úloha (nepovinná)"}>
      <div className="navrhy">
        {otevreno === "osnova" || !osnova
          ? osnovy.map(([id, nazev]) => (
              <Tlacitko
                key={id}
                varianta="obrys"
                aria-pressed={id === osnovaId}
                onClick={() => {
                  setOsnovaId(id);
                  setOtevreno("uloha");
                }}
              >
                {nazev}
              </Tlacitko>
            ))
          : (
            <Tlacitko varianta="obrys" aria-pressed onClick={() => setOtevreno("osnova")}>
              {osnova[1]}
            </Tlacitko>
          )}
      </div>
      {osnova && otevreno !== "osnova" && (
        <div className="navrhy">
          {otevreno === "uloha" || !vybrana || vybrana.osnova_id !== osnovaId ? (
            <>
              {ulohy
                .filter((u) => u.osnova_id === osnovaId)
                .map((u) => (
                  <Tlacitko
                    key={u.id}
                    varianta="obrys"
                    aria-pressed={u.id === vybrana?.id}
                    onClick={() => vybrat_(u.id)}
                  >
                    {u.nazev}
                  </Tlacitko>
                ))}
              {!povinna && vybrana && (
                <Tlacitko varianta="bez-ramu" onClick={() => vybrat_(undefined)}>
                  Bez úlohy
                </Tlacitko>
              )}
            </>
          ) : (
            <Tlacitko varianta="obrys" aria-pressed onClick={() => setOtevreno("uloha")}>
              {vybrana.nazev}
            </Tlacitko>
          )}
        </div>
      )}
    </Blok>
  );
}

// --- dokončení: VZLET TEĎ / Naplánovat / Proběhlý let ---------------------------------------

type Spolecne = {
  nabidky: Nabidky;
  novy: Novy;
  ucel: Ucel;
  letadlo: LetadloNabidka;
  aerovlek: boolean;
  platce: number | "aeroklub" | undefined;
  zavrit: () => void;
};

type Casy = {
  cas_vzletu: string;
  cas_pristani: string;
  pocet_pristani: number;
  cas_pristani_vlecne?: string;
  misto_pristani_id: number | null;
  misto_pristani_popis: string | null;
};

function useUlozit({ nabidky, novy, ucel, letadlo, aerovlek, platce, zavrit }: Spolecne) {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: (a: { akce: "vzlet" | "naplanovat" | "probehly"; casy?: Casy }) => {
      const zpusob = letadlo.kategorie_kod === "KLUZAK" ? novy.zpusob! : "VLASTNI";
      return poslat<Provedeno>("/lety", {
        letadlo_id: letadlo.id,
        ucel_id: ucel.id,
        posadka: Object.entries(novy.osoby).map(([funkce, osoba]) => ({
          osoba_id: osoba,
          funkce_id: Number(funkce),
        })),
        pob: ucel.funkce.length === 0 ? Math.min(novy.pob, letadlo.pocet_mist) : null,
        zpusob_vzletu_id: nabidky.zpusoby.find((z) => z.kod === zpusob)?.id,
        vlecna_id: aerovlek ? novy.vlecna?.id : null,
        vlekar_id: aerovlek ? novy.vlekar : null,
        uloha_id: novy.uloha ?? null,
        platce_id: typeof platce === "number" ? platce : null,
        plati_aeroklub: platce === "aeroklub",
        akce: a.akce,
        misto_vzletu_id: novy.mistoVzletu?.id ?? null,
        misto_vzletu_popis: novy.mistoVzletu?.popis ?? null,
        ...a.casy,
      });
    },
    onSuccess: async (p, a) => {
      // Přehled letů se načte dřív, než se na něj průvodce vrátí (jinak by ukázal starý stav).
      await qc.invalidateQueries({ queryKey: ["lety"], refetchType: "all" });
      qc.invalidateQueries({ queryKey: ["nabidky"] });
      if (a.akce === "vzlet") {
        oznamitAkci(oznamit, p, "vzlet", () =>
          poslat(`/lety/${p.let_id}/zpet`, { akce: "vzlet" })
            .catch((e: Error) => oznamit({ text: e.message, chyba: true }))
            .finally(() => qc.invalidateQueries({ queryKey: ["lety"] })),
        );
      } else if (a.akce === "naplanovat") {
        oznamit({ text: `${p.rejstrik} naplánován` });
      } else {
        const od = hodinyMinuty(a.casy!.cas_vzletu);
        const do_ = hodinyMinuty(a.casy!.cas_pristani);
        oznamit({ text: `${p.rejstrik} proběhlý let ${od}–${do_} uložen` });
      }
      zavrit();
    },
  });
}

function Dokonceni(
  props: Spolecne & { hotovo: boolean; muzeVzlet: boolean; probehly: () => void },
) {
  const ulozit = useUlozit(props);
  const neaktivni = !props.hotovo || ulozit.isPending;
  return (
    <>
      <Hlaska>{ulozit.error?.message}</Hlaska>
      {/* VZLET TEĎ chybí, když letí letadlo nebo vybraná vlečná */}
      {props.muzeVzlet && (
        <Tlacitko
          varianta="modre"
          hlavni
          disabled={neaktivni}
          onClick={() => ulozit.mutate({ akce: "vzlet" })}
        >
          Vzlet teď
        </Tlacitko>
      )}
      <div className="akce-vedle">
        <Tlacitko
          varianta="obrys"
          disabled={neaktivni}
          onClick={() => ulozit.mutate({ akce: "naplanovat" })}
        >
          Naplánovat
        </Tlacitko>
        <Tlacitko varianta="obrys" disabled={neaktivni} onClick={props.probehly}>
          Proběhlý let
        </Tlacitko>
      </div>
    </>
  );
}

// --- proběhlý let: výběr časů prstem ----------------------------------------------------------

type PoleCasu = "vzlet" | "pristani" | "vlecna";

function ProbehlyLet(
  props: Spolecne & {
    spolecne: Omit<Parameters<typeof Obrazovka>[0], "children" | "akce">;
  },
) {
  const { letadlo, aerovlek } = props;
  const ulozit = useUlozit(props);
  const [den, setDen] = useState<"dnes" | "vcera">("dnes");
  const [casy, setCasy] = useState<Record<PoleCasu, number | null>>({
    vzlet: null,
    pristani: null,
    vlecna: null,
  });
  const [aktivni, setAktivni] = useState<PoleCasu | null>("vzlet");
  const [pocet, setPocet] = useState(1);
  const [mistoPristani, setMistoPristani] = useState<Misto | undefined>();

  // Minuty od půlnoci UTC zvoleného dne. Dnes nejde vybrat budoucnost.
  const nyni = ted();
  const zacatekDne =
    Date.UTC(nyni.getUTCFullYear(), nyni.getUTCMonth(), nyni.getUTCDate()) -
    (den === "vcera" ? 86_400_000 : 0);
  const { iso, mistni } = denUtc(zacatekDne);
  const limit = den === "dnes" ? minutyUtc(nyni) : 1439;

  const poradi: PoleCasu[] = aerovlek ? ["vzlet", "pristani", "vlecna"] : ["vzlet", "pristani"];
  const nazvy: Record<PoleCasu, string> = {
    vzlet: "Vzlet",
    pristani: "Přistání",
    vlecna: "Přistání vlečné",
  };
  const nastavit = (pole: PoleCasu, min: number, vybrano: boolean) => {
    setCasy((c) => ({ ...c, [pole]: min }));
    // Po výběru z mřížky se samo otevře další nevyplněné pole (přistání, přistání vlečné).
    if (vybrano) setAktivni(poradi.find((p) => p !== pole && casy[p] === null) ?? null);
  };

  const { vzlet, pristani, vlecna } = casy;
  const dobaLetu = vzlet !== null && pristani !== null ? pristani - vzlet : null;
  const chyba =
    (dobaLetu !== null && dobaLetu < 0) || (vlecna !== null && vzlet !== null && vlecna < vzlet);
  const hotovo =
    poradi.every((p) => casy[p] !== null) && !chyba && poradi.every((p) => casy[p]! <= limit);

  return (
    <Obrazovka
      {...props.spolecne}
      akce={
        <>
          <Hlaska>{ulozit.error?.message}</Hlaska>
          <Tlacitko
            varianta="modre"
            hlavni
            disabled={!hotovo || ulozit.isPending}
            onClick={() =>
              ulozit.mutate({
                akce: "probehly",
                casy: {
                  cas_vzletu: iso(vzlet!),
                  cas_pristani: iso(pristani!),
                  pocet_pristani: pocet,
                  ...(aerovlek ? { cas_pristani_vlecne: iso(vlecna!) } : {}),
                  misto_pristani_id: mistoPristani?.id ?? null,
                  misto_pristani_popis: mistoPristani?.popis ?? null,
                },
              })
            }
          >
            Uložit proběhlý let
          </Tlacitko>
        </>
      }
    >
      <Blok nadpis="Den">
        <div className="volby">
          {(["dnes", "vcera"] as const).map((d) => (
            <Tlacitko key={d} varianta="obrys" aria-pressed={den === d} onClick={() => setDen(d)}>
              {d === "dnes" ? "Dnes" : "Včera"}
            </Tlacitko>
          ))}
        </div>
      </Blok>
      {poradi.map((p) => (
        <VyberCasu
          key={p}
          nadpis={nazvy[p]}
          min={casy[p]}
          otevreno={aktivni === p}
          prepnout={() => setAktivni(aktivni === p ? null : p)}
          nastavit={(min, vybrano) => nastavit(p, min, vybrano)}
          limit={limit}
          mistni={mistni}
        />
      ))}
      {dobaLetu !== null && !chyba && (
        <p>
          Doba letu <b className="cisla">{doba(dobaLetu)}</b>
        </p>
      )}
      {chyba && <p className="text-chyby">Přistání je dřív než vzlet.</p>}
      <Blok nadpis="Místo přistání">
        <VolbaMista nabidky={props.nabidky} misto={mistoPristani} zmenit={setMistoPristani} />
      </Blok>
      {letadlo.kategorie_kod !== "KLUZAK" && (
        <Blok nadpis="Přistání celkem">
          <VolbaPoctu pocet={5} vybrano={pocet} vybrat={setPocet} />
        </Blok>
      )}
    </Obrazovka>
  );
}

/** Řada tlačítek 1 … počet (POB, přistání celkem). */
export function VolbaPoctu({
  pocet,
  vybrano,
  vybrat,
}: {
  pocet: number;
  vybrano: number | null;
  vybrat: (n: number) => void;
}) {
  return (
    <div className="volby-pocet">
      {Array.from({ length: pocet }, (_, k) => k + 1).map((n) => (
        <Tlacitko
          key={n}
          varianta="obrys"
          className="cisla"
          aria-pressed={n === vybrano}
          onClick={() => vybrat(n)}
        >
          {n}
        </Tlacitko>
      ))}
    </div>
  );
}
