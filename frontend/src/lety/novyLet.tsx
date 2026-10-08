import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { poslat } from "../api";
import { doba, hodinyMinuty, stopky, ted } from "../cas";
import { Hlaska } from "../komponenty/Hlaska";
import { Blok, BlokTelo } from "../komponenty/Obrazovka";
import { useOznamit } from "../komponenty/Oznameni";
import { Tlacitko } from "../komponenty/Tlacitko";
import { Udaj, Udaje } from "../komponenty/Udaje";
import { useMujProvoz } from "../provoz/api";
import { useJa } from "../uzivatel";
import { oznamitAkci, type Provedeno } from "./akce";
import type { LetadloNabidka, Nabidky, Ucel } from "./api";
import type { LetPasku } from "./Pasek";
import { jmeno, PIC_NAZEV, rychlaVolba, VolbaOsoby, VolbaPoctu, VolbaUlohy } from "./Volby";
import { denUtc, hhmm, minutyUtc, VolbaCasu } from "./VyberCasu";
import { nazevMista, VyberMista, type Misto } from "./VyberMista";
import "./PanelLetu.css";

// Nový let: rozpracovaný let, pravidla voleb a uložení (docs/modul-lety.md 3.1). Sdílí ho
// mobilní průvodce po krocích (Pruvodce.tsx, maketa pruvodce-mobil-v4.html) a desktopový
// formulář v panelu (deska/PanelNovehoLetu.tsx, docs/modul-desktop.md 3.8) – bloky jsou
// stejné, liší se jen jejich poskládání.

/** Krátké názvy účelů do segmentů (vejdou se čtyři vedle sebe). */
const UCEL_SEGMENT: Record<string, string> = { VYCVIK_SOLO: "Sólo", PREZKOUSENI: "Přezk." };

export type Novy = {
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
  /** prázdné = moje letiště */
  mistoVzletu?: Misto;
  /** Místo přistání (plán, u aerovleku pro kluzák i vlečnou); prázdné = moje letiště. */
  mistoPristani?: Misto;
};

/** Nadpis bloku s povinnou volbou, která ještě chybí. */
export const chybi = (ano: boolean) => ano && <span className="text-chyby">vyberte</span>;

/** Rozpracovaný let a vše, co z něj plyne; `letadloId` = rovnou vybrané letadlo (desktop:
 *  klik na letadlo v řadě letadel). */
export function useNovyLet(nabidky: Nabidky, zavrit: () => void, letadloId?: number) {
  const ja = useJa().data!;
  const provoz = useMujProvoz().data;
  const vProvozu = { osoby: provoz?.osoby ?? [], jaId: ja.osoba_id };
  const mojeId = provoz?.letiste?.id;
  const [novy, setNovy] = useState<Novy>(() => {
    const a = nabidky.letadla.find((x) => x.id === letadloId && !x.mimo_provoz);
    return a ? { osoby: {}, pob: 1, letadlo: a, zpusob: vychoziZpusob(nabidky) } : { osoby: {}, pob: 1 };
  });
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

  /** Vybrat letadlo; účel, který se do něj nevejde, se vrátí na normální (zůstane PIC). */
  const vybratLetadlo = (a: LetadloNabidka) => {
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
      zpusob: novy.zpusob ?? vychoziZpusob(nabidky),
      uloha: undefined,
    });
  };

  /** Vybrat účel: PIC zůstane, ostatní funkce závisí na účelu. */
  const vybratUcel = (u: Ucel) =>
    zmenit({
      ucelId: u.id,
      osoby: Object.fromEntries(
        Object.entries(novy.osoby).filter(([f]) => Number(f) === nabidky.pic_id),
      ),
      uloha: undefined,
      platce: undefined,
    });

  // Rozpracovaný let do pásku nahoře: co je zatím vybrané.
  const zpusobKod = kluzak ? (novy.zpusob ?? "NAVIJAK") : "VLASTNI";
  const rozpracovany: LetPasku | null = letadlo
    ? {
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
          return o
            ? [{ jmeno: o.jmeno, prijmeni: o.prijmeni, funkce: p.funkce, funkce_kod: p.kod }]
            : [];
        }),
      }
    : null;

  // Osoba ve funkci: stejná osoba nemůže mít dvě funkce (ani být vlekařem vlastního vleku).
  const obsazene = (krome: string) => [
    ...pole.filter((p) => `f${p.funkceId}` !== krome).map((p) => novy.osoby[p.funkceId]),
    krome !== "vlekar" && aerovlek ? novy.vlekar : undefined,
  ];

  const hotovo =
    !!letadlo &&
    posadkaHotova &&
    (!ulohaPovinna || novy.uloha !== undefined) &&
    (!aerovlek || (novy.vlecna !== undefined && novy.vlekar !== undefined));
  /** VZLET TEĎ nejde, když letí letadlo nebo vybraná vlečná. */
  const muzeVzlet = !letadlo?.leti_od && !(aerovlek && novy.vlecna?.leti_od);
  const vlecne = nabidky.letadla.filter((a) => a.vlecne && !a.mimo_provoz);

  const upravit = (klic: string) => ({
    upravit: () => setUpravuji(upravuji === klic ? null : klic),
    otevreno: upravuji === klic,
  });
  const platceNazev = platce === "aeroklub" ? "Aeroklub" : platce && jmeno(osoba(platce)!);

  return {
    nabidky,
    zavrit,
    ja,
    vProvozu,
    mojeId,
    novy,
    zmenit,
    setUpravuji,
    letadlo,
    ucely,
    ucel,
    kluzak,
    aerovlek,
    pole,
    posadkaHotova,
    platce,
    platceNazev,
    ulohy,
    ulohaPovinna,
    vybratLetadlo,
    vybratUcel,
    rozpracovany,
    obsazene,
    hotovo,
    muzeVzlet,
    vlecne,
    upravit,
  };
}

export type NovyLet = ReturnType<typeof useNovyLet>;

/** Výchozí způsob vzletu kluzáku podle posledního (db: zpusob_kluzaku), jinak naviják. */
const vychoziZpusob = (nabidky: Nabidky) =>
  nabidky.zpusob_kluzaku === "VLEK" ? ("VLEK" as const) : ("NAVIJAK" as const);

// --- bloky -----------------------------------------------------------------------------------

/** Letadla jako dlaždice ve skupinách podle kategorie (barva podle stavu). */
export function DlazdiceLetadel({ n, poVyberu }: { n: NovyLet; poVyberu?: () => void }) {
  const kategorie = [...new Map(n.nabidky.letadla.map((a) => [a.kategorie_kod, a.kategorie]))];
  return kategorie.map(([kod, nazev]) => (
    <section key={kod} className="skupina-letadel">
      <h2 className="nadpisek">{nazev}</h2>
      <div className="dlazdice-mrizka">
        {n.nabidky.letadla
          .filter((a) => a.kategorie_kod === kod)
          .map((a) => (
            <Dlazdice
              key={a.id}
              letadlo={a}
              vybrana={a.id === n.letadlo?.id}
              vybrat={() => {
                n.vybratLetadlo(a);
                poVyberu?.();
              }}
            />
          ))}
      </div>
    </section>
  ));
}

function Dlazdice({
  letadlo: a,
  vybrana,
  vybrat,
}: {
  letadlo: LetadloNabidka;
  vybrana: boolean;
  vybrat: () => void;
}) {
  const stav = a.mimo_provoz ? "mimo" : a.leti_od ? "vzduch" : a.naplanovan ? "naplanovan" : "";
  // tři řádky: rejstřík · typ · stav (mimo provoz, letí, naplánován); soukromé = šedý rejstřík
  return (
    <button
      type="button"
      title={a.soukrome ? "soukromé letadlo" : undefined}
      className={["dlazdice", "panel-letu", a.soukrome && "soukrome", stav, vybrana && "vybrana"]
        .filter(Boolean)
        .join(" ")}
      disabled={a.mimo_provoz}
      aria-pressed={vybrana}
      onClick={vybrat}
    >
      <span className="dlazdice-rejstrik">{a.rejstrik}</span>
      <span className="dlazdice-typ male seda">{a.typ}</span>
      {/* řádek stavu mají všechny dlaždice (prázdný = nezlomitelná mezera, jinak by se
          ztratil) – stejná výška bez ohledu na obsah */}
      <span className="dlazdice-stav cisla">
        {a.mimo_provoz
          ? "mimo provoz"
          : a.leti_od
            ? `letí ${stopky(a.leti_od, ted()).slice(0, -3)}`
            : a.naplanovan
              ? "naplánován"
              : " "}
      </span>
    </button>
  );
}

export function BlokUcelu({ n }: { n: NovyLet }) {
  return (
    <Blok nadpis="Účel">
      <BlokTelo>
        <div className="segmenty">
          {n.ucely.map((u) => (
            <Tlacitko key={u.id} aria-pressed={u.id === n.ucel.id} onClick={() => n.vybratUcel(u)}>
              {UCEL_SEGMENT[u.kod] ?? u.nazev}
            </Tlacitko>
          ))}
        </div>
      </BlokTelo>
    </Blok>
  );
}

/** Pole posádky podle účelu (PIC, žák, dozor, přezkoušený) – každé ve svém bloku. */
export function BlokyPosadky({ n }: { n: NovyLet }) {
  const letadlo = n.letadlo!;
  return n.pole.map((p) => (
    <Blok key={p.funkceId} nadpis={p.nazev} vpravo={chybi(!n.novy.osoby[p.funkceId])}>
      <BlokTelo>
        <VolbaOsoby
          osoby={n.nabidky.osoby}
          jaId={n.ja.osoba_id}
          rychle={rychlaVolba(
            n.nabidky.osoby,
            { ucel: n.ucel.kod, funkce: p.kod, kategorie: letadlo.kategorie_kod },
            [n.ja.osoba_id, ...letadlo.nedavni],
            n.vProvozu,
          )}
          filtr={n.vProvozu.osoby.length}
          vybrana={n.novy.osoby[p.funkceId]}
          vyloucit={n.obsazene(`f${p.funkceId}`)}
          vybrat={(id) =>
            n.zmenit({ osoby: { ...n.novy.osoby, [p.funkceId]: id }, platce: undefined })
          }
        />
      </BlokTelo>
    </Blok>
  ));
}

/** POB jen u účelu bez dalších funkcí na vícemístném letadle (jinak se odvodí z posádky). */
export function BlokPob({ n }: { n: NovyLet }) {
  const letadlo = n.letadlo!;
  if (n.ucel.funkce.length > 0 || letadlo.pocet_mist <= 1) return null;
  return (
    <Blok nadpis="POB">
      <BlokTelo>
        <VolbaPoctu
          pocet={letadlo.pocet_mist}
          vybrano={n.novy.pob}
          vybrat={(pob) => n.zmenit({ pob })}
        />
      </BlokTelo>
    </Blok>
  );
}

/** Způsob vzletu kluzáku (naviják, aerovlek). */
export function BlokZpusobu({ n }: { n: NovyLet }) {
  if (!n.kluzak) return null;
  return (
    <Blok nadpis="Způsob vzletu">
      <BlokTelo>
        <div className="segmenty">
          {(["NAVIJAK", "VLEK"] as const).map((z) => (
            <Tlacitko key={z} aria-pressed={n.novy.zpusob === z} onClick={() => n.zmenit({ zpusob: z })}>
              {n.nabidky.zpusoby.find((zp) => zp.kod === z)?.nazev}
            </Tlacitko>
          ))}
        </div>
      </BlokTelo>
    </Blok>
  );
}

/** Aerovlek: vlečná a vlekař (předvyplní se vlekař posledního vleku, není-li v posádce). */
export function BlokVleku({ n }: { n: NovyLet }) {
  if (!n.aerovlek) return null;
  const { novy } = n;
  return (
    <Blok
      nadpis="Vlečná a vlekař"
      vpravo={chybi(novy.vlecna === undefined || novy.vlekar === undefined)}
    >
      <BlokTelo>
        <div className="cipy">
          {n.vlecne.map((a) => (
            <Tlacitko
              key={a.id}
              aria-pressed={a.id === novy.vlecna?.id}
              onClick={() => {
                const posledni = a.posledni_vlekar ?? undefined;
                const vPosadce = Object.values(novy.osoby).includes(posledni ?? -1);
                n.zmenit({ vlecna: a, vlekar: novy.vlekar ?? (vPosadce ? undefined : posledni) });
              }}
            >
              {a.rejstrik}
              {a.leti_od && <span className="male"> · letí</span>}
            </Tlacitko>
          ))}
        </div>
        <VolbaOsoby
          osoby={n.nabidky.osoby}
          jaId={n.ja.osoba_id}
          rychle={rychlaVolba(
            n.nabidky.osoby,
            { ucel: null, funkce: "PIC", kategorie: novy.vlecna?.kategorie_kod },
            [],
            n.vProvozu,
          )}
          filtr={n.vProvozu.osoby.length}
          vybrana={novy.vlekar}
          vyloucit={n.obsazene("vlekar")}
          vybrat={(id) => n.zmenit({ vlekar: id })}
        />
      </BlokTelo>
    </Blok>
  );
}

export function BlokUlohy({ n }: { n: NovyLet }) {
  if (n.ulohy.length === 0) return null;
  return (
    <Blok
      nadpis="Úloha"
      vpravo={n.ulohaPovinna ? chybi(n.novy.uloha === undefined) : <span>nepovinná</span>}
    >
      <BlokTelo>
        <VolbaUlohy
          key={n.ucel.id}
          ulohy={n.ulohy}
          povinna={n.ulohaPovinna}
          vybrana={n.ulohy.find((u) => u.id === n.novy.uloha)}
          vybrat={(id) => n.zmenit({ uloha: id })}
        />
      </BlokTelo>
    </Blok>
  );
}

/** Místo vzletu, místo přistání a plátce (předvyplněné, ťuknutím se změní). */
export function BlokDalsichUdaju({ n }: { n: NovyLet }) {
  const { nabidky, novy, mojeId, platce } = n;
  return (
    <Blok nadpis="Další údaje">
      <Udaje>
        <Udaj popisek="Místo vzletu" hodnota={nazevMista(nabidky, novy.mistoVzletu, mojeId)} {...n.upravit("misto")}>
          <VyberMista
            nabidky={nabidky}
            ulozit={(id, popis) => n.zmenit({ mistoVzletu: id === mojeId ? undefined : { id, popis } })}
          />
        </Udaj>
        <Udaj
          popisek="Místo přistání"
          hodnota={nazevMista(nabidky, novy.mistoPristani, mojeId)}
          {...n.upravit("pristani")}
        >
          <VyberMista
            nabidky={nabidky}
            ulozit={(id, popis) =>
              n.zmenit({ mistoPristani: id === mojeId ? undefined : { id, popis } })
            }
          />
        </Udaj>
        <Udaj popisek="Platí" hodnota={n.platceNazev} {...n.upravit("platce")}>
          <VolbaOsoby
            osoby={nabidky.osoby}
            jaId={n.ja.osoba_id}
            rychle={n.pole.map((p) => novy.osoby[p.funkceId]).filter((id): id is number => !!id)}
            vybrana={typeof platce === "number" ? platce : undefined}
            vybrat={(id) => n.zmenit({ platce: id })}
            menit
            pred={
              <Tlacitko aria-pressed={platce === "aeroklub"} onClick={() => n.zmenit({ platce: "aeroklub" })}>
                Aeroklub
              </Tlacitko>
            }
          />
        </Udaj>
      </Udaje>
    </Blok>
  );
}

// --- uložení: VZLET TEĎ / Naplánovat / Proběhlý let ---------------------------------------

type Casy = {
  cas_vzletu: string;
  cas_pristani: string;
  pocet_pristani: number;
  cas_pristani_vlecne?: string;
};

function useUlozit({ nabidky, novy, ucel, letadlo, aerovlek, platce, zavrit }: NovyLet) {
  const qc = useQueryClient();
  const oznamit = useOznamit();
  return useMutation({
    mutationFn: (a: { akce: "vzlet" | "naplanovat" | "probehly"; casy?: Casy }) => {
      const zpusob = letadlo!.kategorie_kod === "KLUZAK" ? novy.zpusob! : "VLASTNI";
      return poslat<Provedeno>("/lety", {
        letadlo_id: letadlo!.id,
        ucel_id: ucel.id,
        posadka: Object.entries(novy.osoby).map(([funkce, osoba]) => ({
          osoba_id: osoba,
          funkce_id: Number(funkce),
        })),
        pob: ucel.funkce.length === 0 ? Math.min(novy.pob, letadlo!.pocet_mist) : null,
        zpusob_vzletu_id: nabidky.zpusoby.find((z) => z.kod === zpusob)?.id,
        vlecna_id: aerovlek ? novy.vlecna?.id : null,
        vlekar_id: aerovlek ? novy.vlekar : null,
        uloha_id: novy.uloha ?? null,
        platce_id: typeof platce === "number" ? platce : null,
        plati_aeroklub: platce === "aeroklub",
        akce: a.akce,
        misto_vzletu_id: novy.mistoVzletu?.id ?? null,
        misto_vzletu_popis: novy.mistoVzletu?.popis ?? null,
        misto_pristani_id: novy.mistoPristani?.id ?? null,
        misto_pristani_popis: novy.mistoPristani?.popis ?? null,
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

/** VZLET TEĎ (chybí, když letí letadlo nebo vybraná vlečná) · Naplánovat · Proběhlý let. */
export function Dokonceni({ n, probehly }: { n: NovyLet; probehly: () => void }) {
  const ulozit = useUlozit(n);
  const neaktivni = !n.hotovo || ulozit.isPending;
  return (
    <>
      <Hlaska>{ulozit.error?.message}</Hlaska>
      {n.muzeVzlet && (
        <Tlacitko varianta="modre" hlavni disabled={neaktivni} onClick={() => ulozit.mutate({ akce: "vzlet" })}>
          Vzlet teď
        </Tlacitko>
      )}
      <div className="akce-vedle">
        <Tlacitko varianta="obrys" disabled={neaktivni} onClick={() => ulozit.mutate({ akce: "naplanovat" })}>
          Naplánovat
        </Tlacitko>
        <Tlacitko varianta="obrys" disabled={neaktivni} onClick={probehly}>
          Proběhlý let
        </Tlacitko>
      </div>
    </>
  );
}

// --- proběhlý let: výběr časů ----------------------------------------------------------------

type PoleCasu = "vzlet" | "pristani" | "vlecna";

/** Části obrazovky proběhlého letu – poskládá je průvodce (mobil) nebo panel (desktop). */
export type CastiProbehleho = {
  /** Obsah přihrádky času na rozpracovaném pásku (vzlet nad přistáním). */
  cas: ReactNode;
  bloky: ReactNode;
  akce: ReactNode;
};

/** Proběhlý let: den, časy vzletu a přistání (a přistání vlečné), místo přistání, přistání
 *  celkem; uložit. `obal` poskládá části do obrazovky. */
export function ProbehlyLet({
  n,
  obal,
}: {
  n: NovyLet;
  obal: (casti: CastiProbehleho) => ReactNode;
}) {
  const { letadlo, aerovlek, nabidky, novy, mojeId } = n;
  const ulozit = useUlozit(n);
  const [den, setDen] = useState<"dnes" | "vcera">("dnes");
  const [casy, setCasy] = useState<Record<PoleCasu, number | null>>({
    vzlet: null,
    pristani: null,
    vlecna: null,
  });
  const [aktivni, setAktivni] = useState<PoleCasu | null>("vzlet");
  const [pocet, setPocet] = useState(1);
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

  return obal({
    cas: (
      <>
        <b>{vzlet === null ? "—:—" : hhmm(vzlet)}</b>
        <span className="seda">{pristani === null ? "—:—" : hhmm(pristani)}</span>
      </>
    ),
    akce: (
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
              },
            })
          }
        >
          Uložit proběhlý let
        </Tlacitko>
      </>
    ),
    bloky: (
      <>
        <Blok nadpis="Den">
          <BlokTelo>
            <div className="segmenty">
              {(["dnes", "vcera"] as const).map((d) => (
                <Tlacitko key={d} aria-pressed={den === d} onClick={() => setDen(d)}>
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
              hodnota={nazevMista(nabidky, novy.mistoPristani, mojeId)}
              upravit={() => setUpravuji(!upravuji)}
              otevreno={upravuji}
            >
              <VyberMista
                nabidky={nabidky}
                ulozit={(id, popis) => {
                  n.zmenit({ mistoPristani: id === mojeId ? undefined : { id, popis } });
                  setUpravuji(false);
                }}
              />
            </Udaj>
          </Udaje>
        </Blok>
        {letadlo!.kategorie_kod !== "KLUZAK" && (
          <Blok nadpis="Přistání celkem">
            <BlokTelo>
              <VolbaPoctu pocet={5} vybrano={pocet} vybrat={setPocet} />
            </BlokTelo>
          </Blok>
        )}
      </>
    ),
  });
}
