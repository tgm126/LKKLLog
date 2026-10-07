import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router";

import { poslat } from "../api";
import { doba, hodinyMinuty, stopky, ted } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, BlokTelo, Obrazovka } from "../komponenty/Obrazovka";
import { useOznamit } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { useJa } from "../uzivatel";
import { oznamitAkci, type Provedeno } from "./akce";
import { useNabidky, type LetadloNabidka, type Nabidky, type Ucel } from "./api";
import { PolovinaPasku, type LetPasku } from "./Pasek";
import { Udaj, Udaje } from "../komponenty/Udaje";
import {
  jmeno,
  PIC_NAZEV,
  rychlaVolba,
  VolbaOsoby,
  VolbaPoctu,
  VolbaUlohy,
} from "./Volby";
import { denUtc, hhmm, minutyUtc, VolbaCasu } from "./VyberCasu";
import { nazevMista, VyberMista, type Misto } from "./VyberMista";
import "./Pruvodce.css";

// Průvodce novým letem podle makety docs/navrhy/pruvodce-mobil-v4.html:
// 1 letadlo → 2 posádka → 3 let (u kluzáku vzlet a vlek, úloha, další údaje) → VZLET TEĎ /
// Naplánovat / Proběhlý let (výběr časů prstem). Od kroku 2 je nahoře rozpracovaný pásek
// letu, který se plní s každou volbou.

/** Krátké názvy účelů do segmentů (vejdou se čtyři vedle sebe). */
const UCEL_SEGMENT: Record<string, string> = { VYCVIK_SOLO: "Sólo", PREZKOUSENI: "Přezk." };

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

/** Ukazatel postupu pod horní lištou: tři díly, hotové modře. */
function Postup({ krok }: { krok: Krok }) {
  const hotovo = krok === "casy" ? 3 : krok;
  return (
    <div className="postup" aria-hidden>
      {[1, 2, 3].map((k) => (
        <span key={k} className={k <= hotovo ? "hotovo" : undefined} />
      ))}
    </div>
  );
}

/** Nadpis bloku s povinnou volbou, která ještě chybí. */
const chybi = (ano: boolean) => ano && <span className="text-chyby">vyberte</span>;

function PruvodceKroky({ nabidky, zavrit }: { nabidky: Nabidky; zavrit: () => void }) {
  const ja = useJa().data!;
  const [krok, setKrok] = useState<Krok>(1);
  const [novy, setNovy] = useState<Novy>({ osoby: {}, pob: 1 });
  const [upravuji, setUpravuji] = useState<string | null>(null);
  const zmenit = (zmena: Partial<Novy>) => {
    setNovy((n) => ({ ...n, ...zmena }));
    setUpravuji(null);
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
    { funkceId: nabidky.pic_id, kod: "PIC", funkce: "PIC", nazev: PIC_NAZEV[ucel.kod] ?? "PIC" },
    ...ucel.funkce.map((f) => ({ funkceId: f.id, kod: f.kod, funkce: f.nazev, nazev: f.nazev })),
  ];
  const posadkaHotova = pole.every((p) => novy.osoby[p.funkceId]);

  // Výchozí plátce: kdo je na palubě s jinou funkcí než PIC (žák, přezkoušený), jinak PIC.
  const naPalube = ucel.funkce.find((f) => f.na_palube && novy.osoby[f.id]);
  const vychoziPlatce = novy.osoby[naPalube?.id ?? nabidky.pic_id];
  const platce = novy.platce ?? vychoziPlatce;

  const ulohy = letadlo
    ? nabidky.ulohy.filter(
        (u) =>
          u.ucel_id === ucel.id &&
          (u.kategorie_kod === null || u.kategorie_kod === letadlo.kategorie_kod),
      )
    : [];
  // Úloha je povinná podle účelu, ale jen když pro účel a kategorii letadla nějaká existuje
  // (stejné pravidlo hlídá databáze).
  const ulohaPovinna = ucel.uloha_povinna && ulohy.length > 0;

  const zpet = () => {
    setUpravuji(null);
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
    zpet,
    zpetPopis: krok === 1 ? ("Zavřít" as const) : ("Zpět" as const),
    nadpis: krok === 1 || !letadlo ? "Nový let" : letadlo.rejstrik,
    vpravo: <span className="nadpisek">{nadpisKroku[krok]}</span>,
    pod: <Postup krok={krok} />,
  };

  // --- krok 1: letadlo -----------------------------------------------------------------------
  if (krok === 1 || !letadlo) {
    const kategorie = [...new Map(nabidky.letadla.map((a) => [a.kategorie_kod, a.kategorie]))];
    return (
      <Obrazovka {...spolecne}>
        {kategorie.map(([kod, nazev]) => (
          <section key={kod} className="skupina-letadel">
            <h2 className="nadpisek">{nazev}</h2>
            <div className="dlazdice-mrizka">
              {nabidky.letadla
                .filter((a) => a.kategorie_kod === kod)
                .map((a) => (
                  <Dlazdice
                    key={a.id}
                    letadlo={a}
                    vybrana={a.id === letadlo?.id}
                    vybrat={() => {
                      // účel, který se do letadla nevejde, se vrátí na normální (zůstane PIC)
                      const ucelSedi = ucelyPro(a).some((u) => u.id === novy.ucelId);
                      zmenit({
                        letadlo: a,
                        ...(ucelSedi
                          ? {}
                          : {
                              ucelId: undefined,
                              osoby: Object.fromEntries(
                                Object.entries(novy.osoby).filter(
                                  ([f]) => Number(f) === nabidky.pic_id,
                                ),
                              ),
                              platce: undefined,
                            }),
                        pob: Math.min(novy.pob, a.pocet_mist),
                        zpusob:
                          novy.zpusob ?? (nabidky.zpusob_kluzaku === "VLEK" ? "VLEK" : "NAVIJAK"),
                        uloha: undefined,
                      });
                      setKrok(2);
                    }}
                  />
                ))}
            </div>
          </section>
        ))}
      </Obrazovka>
    );
  }

  // Rozpracovaný let do pásku nahoře: co je zatím vybrané.
  const zpusobKod = kluzak ? (novy.zpusob ?? "NAVIJAK") : "VLASTNI";
  const rozpracovany: LetPasku = {
    stav: "ROZPRACOVANY",
    rejstrik: letadlo.rejstrik,
    typ: letadlo.typ,
    je_vlecny: false,
    ucel: ucel.nazev,
    ucel_kod: ucel.kod,
    zpusob_vzletu: nabidky.zpusoby.find((z) => z.kod === zpusobKod)?.nazev ?? "",
    zpusob_vzletu_kod: zpusobKod,
    cas_vzletu: null,
    cas_pristani: null,
    doba_uctovana_min: null,
    pocet_pristani: null,
    uloha: nabidky.ulohy.find((u) => u.id === novy.uloha)?.nazev ?? null,
    varovani: null,
    pob:
      ucel.funkce.length === 0
        ? Math.min(novy.pob, letadlo.pocet_mist)
        : 1 + ucel.funkce.filter((f) => f.na_palube).length,
    posadka: pole.flatMap((p) => {
      const o = osoba(novy.osoby[p.funkceId]);
      return o ? [{ jmeno: o.jmeno, prijmeni: o.prijmeni, funkce: p.funkce, funkce_kod: p.kod }] : [];
    }),
  };
  const pasek = (cas?: ReactNode) => (
    <div className="let rozpracovany">
      <PolovinaPasku
        let={rozpracovany}
        cas={
          cas ??
          (aerovlek && novy.vlecna ? (
            <>
              <b>{novy.vlecna.rejstrik}</b>
              <span className="male seda">vlečná</span>
            </>
          ) : (
            <span className="male seda">nový</span>
          ))
        }
      />
    </div>
  );

  // Osoba ve funkci: stejná osoba nemůže mít dvě funkce (ani být vlekařem vlastního vleku).
  const obsazene = (krome: string) => [
    ...pole.filter((p) => `f${p.funkceId}` !== krome).map((p) => novy.osoby[p.funkceId]),
    krome !== "vlekar" && aerovlek ? novy.vlekar : undefined,
  ];

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
              setUpravuji(null);
              setKrok(3);
            }}
          >
            Dál
          </Tlacitko>
        }
      >
        {pasek()}
        <Blok nadpis="Účel">
          <BlokTelo>
            <div className="segmenty">
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
                  {UCEL_SEGMENT[u.kod] ?? u.nazev}
                </Tlacitko>
              ))}
            </div>
          </BlokTelo>
        </Blok>
        {pole.map((p) => (
          <Blok key={p.funkceId} nadpis={p.nazev} vpravo={chybi(!novy.osoby[p.funkceId])}>
            <BlokTelo>
              <VolbaOsoby
                osoby={nabidky.osoby}
                jaId={ja.osoba_id}
                rychle={rychlaVolba(
                  nabidky.osoby,
                  { ucel: ucel.kod, funkce: p.kod, kategorie: letadlo.kategorie_kod },
                  [ja.osoba_id, ...letadlo.nedavni],
                )}
                vybrana={novy.osoby[p.funkceId]}
                vyloucit={obsazene(`f${p.funkceId}`)}
                vybrat={(id) => zmenit({ osoby: { ...novy.osoby, [p.funkceId]: id }, platce: undefined })}
              />
            </BlokTelo>
          </Blok>
        ))}
        {pob && (
          <Blok nadpis="POB">
            <BlokTelo>
              <VolbaPoctu
                pocet={letadlo.pocet_mist}
                vybrano={novy.pob}
                vybrat={(n) => zmenit({ pob: n })}
              />
            </BlokTelo>
          </Blok>
        )}
      </Obrazovka>
    );
  }

  // --- krok 3: let a proběhlý let ------------------------------------------------------------
  const hotovo =
    posadkaHotova &&
    (!ulohaPovinna || novy.uloha !== undefined) &&
    (!aerovlek || (novy.vlecna !== undefined && novy.vlekar !== undefined));
  const muzeVzlet = !letadlo.leti_od && !(aerovlek && novy.vlecna?.leti_od);
  const vlecne = nabidky.letadla.filter((a) => a.vlecne && !a.mimo_provoz);
  const props = { nabidky, novy, ucel, letadlo, aerovlek, platce, zavrit };

  if (krok === "casy") {
    return <ProbehlyLet {...props} spolecne={spolecne} pasek={pasek} />;
  }

  const upravit = (klic: string) => ({
    upravit: () => setUpravuji(upravuji === klic ? null : klic),
    otevreno: upravuji === klic,
  });
  const platceNazev = platce === "aeroklub" ? "Aeroklub" : platce && jmeno(osoba(platce)!);

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
      {pasek()}
      {kluzak && (
        <Blok nadpis="Způsob vzletu">
          <BlokTelo>
            <div className="segmenty">
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
          </BlokTelo>
        </Blok>
      )}
      {aerovlek && (
        <Blok
          nadpis="Vlečná a vlekař"
          vpravo={chybi(novy.vlecna === undefined || novy.vlekar === undefined)}
        >
          <BlokTelo>
            <div className="cipy">
              {vlecne.map((a) => (
                <Tlacitko
                  key={a.id}
                  varianta="obrys"
                  aria-pressed={a.id === novy.vlecna?.id}
                  onClick={() => {
                    // vlekař posledního vleku – jen když není v posádce kluzáku
                    const posledni = a.posledni_vlekar ?? undefined;
                    const vPosadce = Object.values(novy.osoby).includes(posledni ?? -1);
                    zmenit({ vlecna: a, vlekar: novy.vlekar ?? (vPosadce ? undefined : posledni) });
                  }}
                >
                  {a.rejstrik}
                  {a.leti_od && <span className="male"> · letí</span>}
                </Tlacitko>
              ))}
            </div>
            <VolbaOsoby
              osoby={nabidky.osoby}
              jaId={ja.osoba_id}
              rychle={rychlaVolba(
                nabidky.osoby,
                { ucel: null, funkce: "PIC", kategorie: novy.vlecna?.kategorie_kod },
                [],
              )}
              vybrana={novy.vlekar}
              vyloucit={obsazene("vlekar")}
              vybrat={(id) => zmenit({ vlekar: id })}
            />
          </BlokTelo>
        </Blok>
      )}
      {ulohy.length > 0 && (
        <Blok
          nadpis="Úloha"
          vpravo={ulohaPovinna ? chybi(novy.uloha === undefined) : <span>nepovinná</span>}
        >
          <BlokTelo>
            <VolbaUlohy
              key={ucel.id}
              ulohy={ulohy}
              povinna={ulohaPovinna}
              vybrana={ulohy.find((u) => u.id === novy.uloha)}
              vybrat={(id) => zmenit({ uloha: id })}
            />
          </BlokTelo>
        </Blok>
      )}
      <Blok nadpis="Další údaje">
        <Udaje>
          <Udaj popisek="Místo vzletu" hodnota={nazevMista(nabidky, novy.mistoVzletu)} {...upravit("misto")}>
            <VyberMista
              nabidky={nabidky}
              ulozit={(id, popis) =>
                zmenit({
                  mistoVzletu: id === nabidky.letiste.find((l) => l.domovske)?.id ? undefined : { id, popis },
                })
              }
            />
          </Udaj>
          <Udaj popisek="Platí" hodnota={platceNazev} {...upravit("platce")}>
            <VolbaOsoby
              osoby={nabidky.osoby}
              jaId={ja.osoba_id}
              rychle={pole.map((p) => novy.osoby[p.funkceId]).filter((id): id is number => !!id)}
              vybrana={typeof platce === "number" ? platce : undefined}
              vybrat={(id) => zmenit({ platce: id })}
              menit
              pred={
                <Tlacitko
                  varianta="obrys"
                  aria-pressed={platce === "aeroklub"}
                  onClick={() => zmenit({ platce: "aeroklub" })}
                >
                  Aeroklub
                </Tlacitko>
              }
            />
          </Udaj>
        </Udaje>
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
  const stav = a.mimo_provoz ? "mimo" : a.leti_od ? "leti" : a.naplanovan ? "planovan" : "";
  const typ = [a.typ, a.vlecne && "vlečná", a.soukrome && "soukromé"].filter(Boolean).join(" · ");
  return (
    <button
      type="button"
      className={["dlazdice", stav, vybrana && "vybrana"].filter(Boolean).join(" ")}
      disabled={a.mimo_provoz}
      aria-pressed={vybrana}
      onClick={vybrat}
    >
      <span className="dlazdice-rejstrik">{a.rejstrik}</span>
      <span className="male seda">{typ}</span>
      {a.leti_od && (
        <span className="dlazdice-stav cisla">letí {stopky(a.leti_od, ted()).slice(0, -3)}</span>
      )}
      {!a.leti_od && a.naplanovan && <span className="dlazdice-stav">naplánován</span>}
      {a.mimo_provoz && <span className="dlazdice-stav">mimo provoz</span>}
    </button>
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
    pasek: (cas?: ReactNode) => ReactNode;
  },
) {
  const { letadlo, aerovlek, nabidky } = props;
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
  const [upravuji, setUpravuji] = useState(false);

  // Minuty od půlnoci UTC zvoleného dne. Dnes nejde vybrat budoucnost.
  const nyni = ted();
  const zacatekDne =
    Date.UTC(nyni.getUTCFullYear(), nyni.getUTCMonth(), nyni.getUTCDate()) -
    (den === "vcera" ? 86_400_000 : 0);
  const { iso, mistni } = denUtc(zacatekDne);
  const limit = den === "dnes" ? minutyUtc(nyni) : 1439;

  const poradi: PoleCasu[] = aerovlek ? ["vzlet", "pristani", "vlecna"] : ["vzlet", "pristani"];
  const nazvy: Record<PoleCasu, string> = { vzlet: "Vzlet", pristani: "Přistání", vlecna: "Vlečná" };
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
  const mistniCas = aktivni && casy[aktivni] !== null ? `místní ${mistni(casy[aktivni]!)}` : null;

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
      {props.pasek(
        <>
          <b>{vzlet === null ? "—:—" : hhmm(vzlet)}</b>
          <span className="seda">{pristani === null ? "—:—" : hhmm(pristani)}</span>
        </>,
      )}
      <Blok nadpis="Den">
        <BlokTelo>
          <div className="segmenty">
            {(["dnes", "vcera"] as const).map((d) => (
              <Tlacitko key={d} varianta="obrys" aria-pressed={den === d} onClick={() => setDen(d)}>
                {d === "dnes" ? "Dnes" : "Včera"}
              </Tlacitko>
            ))}
          </div>
        </BlokTelo>
      </Blok>
      <Blok nadpis="Časy (UTC)" vpravo={mistniCas}>
        <BlokTelo>
          <VolbaCasu
            pole={poradi.map((p) => ({ klic: p, nazev: nazvy[p], min: casy[p] }))}
            aktivni={aktivni}
            aktivovat={setAktivni}
            nastavit={nastavit}
            limit={limit}
            doplnek={
              chyba ? (
                <span className="text-chyby">Přistání je dřív než vzlet.</span>
              ) : (
                dobaLetu !== null && (
                  <>
                    Doba letu <b className="cisla">{doba(dobaLetu)}</b>
                  </>
                )
              )
            }
          />
        </BlokTelo>
      </Blok>
      <Blok nadpis="Další údaje">
        <Udaje>
          <Udaj
            popisek="Místo přistání"
            hodnota={nazevMista(nabidky, mistoPristani)}
            upravit={() => setUpravuji(!upravuji)}
            otevreno={upravuji}
          >
            <VyberMista
              nabidky={nabidky}
              ulozit={(id, popis) => {
                const domovske = nabidky.letiste.find((l) => l.domovske)?.id;
                setMistoPristani(id === domovske ? undefined : { id, popis });
                setUpravuji(false);
              }}
            />
          </Udaj>
        </Udaje>
      </Blok>
      {letadlo.kategorie_kod !== "KLUZAK" && (
        <Blok nadpis="Přistání celkem">
          <BlokTelo>
            <VolbaPoctu pocet={5} vybrano={pocet} vybrat={setPocet} />
          </BlokTelo>
        </Blok>
      )}
    </Obrazovka>
  );
}
