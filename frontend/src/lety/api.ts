// Data letů ze serveru (backend/app/lety.py).
import { useQuery } from "@tanstack/react-query";

import { ziskat } from "../api";
import { nastavitCasServeru } from "../cas";

export type Den = {
  den: string;
  ted: string;
  /** Moje letiště na dnešek (můj provoz, jinak domovské); sluneční časy jsou pro ně. */
  letiste: { id: number; kod: string; nazev: string; domovske: boolean } | null;
  slunce: { tb: string | null; sr: string | null; ss: string | null; te: string | null };
};

export type Clen = { jmeno: string; prijmeni: string; funkce: string; funkce_kod: string };

export type Stav = "NAPLANOVAN" | "VE_VZDUCHU" | "UKONCEN" | "ZRUSEN";

export type Pasek = {
  id: number;
  stav: Stav;
  rejstrik: string;
  typ: string;
  kategorie_kod: string;
  ucel: string | null;
  ucel_kod: string | null;
  zpusob_vzletu: string;
  zpusob_vzletu_kod: string;
  je_vlecny: boolean;
  vlecny_let_id: number | null;
  vleceny_let_id: number | null;
  vlek_rejstrik: string | null;
  misto_vzletu: string | null;
  misto_pristani: string | null;
  cas_vzletu: string | null;
  cas_pristani: string | null;
  doba_uctovana_min: number | null;
  pocet_pristani: number | null;
  /** Na palubě (u výcviku spočítaný z posádky). */
  pob: number;
  uloha: string | null;
  pocet_tg: number;
  posadka: Clen[];
  duvod_zruseni: string | null;
  zruseno: string | null;
  dodatecne: boolean;
  zalozeno: string;
  varovani: string | null;
};

/** Den do hlavičky (datum, sluneční časy); jednou za minutu kvůli přechodu půlnoci. */
export function useDen() {
  return useQuery({
    queryKey: ["den"],
    queryFn: async () => {
      const den = await ziskat<Den>("/den");
      nastavitCasServeru(den.ted);
      return den;
    },
    refetchInterval: 60_000,
  });
}

/** Lety dne; obnovují se samy každých 10 s a po návratu do aplikace (docs/modul-lety.md 3.2). */
export function useLety() {
  return useQuery({
    queryKey: ["lety"],
    queryFn: async () => {
      const lety = await ziskat<{ ted: string; lety: Pasek[] }>("/lety");
      nastavitCasServeru(lety.ted);
      return lety.lety;
    },
    refetchInterval: 10_000,
  });
}

// --- průvodce novým letem --------------------------------------------------------------------

export type LetadloNabidka = {
  id: number;
  rejstrik: string;
  typ: string;
  kategorie: string;
  kategorie_kod: string;
  pocet_mist: number;
  vlecne: boolean;
  soukrome: boolean;
  mimo_provoz: boolean;
  leti_od: string | null;
  naplanovan: boolean;
  /** Naposledy létající na letadle (id osob, od posledního). */
  nedavni: number[];
  posledni_vlekar: number | null;
};

export type Funkce = { id: number; kod: string; nazev: string; na_palube: boolean };
export type Ucel = { id: number; kod: string; nazev: string; uloha_povinna: boolean; funkce: Funkce[] };
/** Role, kterou osoba smí zastat podle oprávnění (db/024): účel (null = vlečný let), funkce,
 *  kategorie letadla. */
export type Role = { ucel: string | null; funkce: string; kategorie: string };
export type Osoba = { id: number; jmeno: string; prijmeni: string; role: Role[] };
export type Uloha = {
  id: number;
  nazev: string;
  osnova_id: number;
  osnova: string;
  ucel_id: number;
  /** Prázdná = obecná úloha pro všechny kategorie. */
  kategorie_kod: string | null;
};

export type Nabidky = {
  letadla: LetadloNabidka[];
  ucely: Ucel[];
  pic_id: number;
  zpusoby: { id: number; kod: string; nazev: string }[];
  duvody_zruseni: { id: number; kod: string; nazev: string }[];
  letiste: { id: number; kod: string; nazev: string; domovske: boolean }[];
  osoby: Osoba[];
  ulohy: Uloha[];
  zpusob_kluzaku: string | null;
};

export function useNabidky() {
  return useQuery({
    queryKey: ["nabidky"],
    queryFn: () => ziskat<Nabidky>("/lety/nabidky"),
    staleTime: 0,
  });
}

// --- detail letu -----------------------------------------------------------------------------

export type ClenDetail = {
  osoba_id: number;
  jmeno: string;
  prijmeni: string;
  funkce_id: number;
  funkce_kod: string;
  funkce: string;
};

export type DetailLetu = {
  id: number;
  verze: number;
  stav: Stav;
  letadlo_id: number;
  rejstrik: string;
  typ: string;
  kategorie: string;
  kategorie_kod: string;
  pocet_mist: number;
  ucel_id: number | null;
  ucel: string | null;
  ucel_kod: string | null;
  uloha_id: number | null;
  uloha: string | null;
  zpusob_vzletu: string;
  zpusob_vzletu_kod: string;
  je_vlecny: boolean;
  misto_vzletu_id: number | null;
  misto_vzletu_popis: string | null;
  misto_vzletu: string | null;
  misto_pristani_id: number | null;
  misto_pristani_popis: string | null;
  misto_pristani: string | null;
  cas_vzletu: string | null;
  cas_pristani: string | null;
  doba_min: number | null;
  doba_uctovana_min: number | null;
  pocet_pristani: number | null;
  pob: number | null;
  /** Zadaný počet (u výcviku, sóla a přezkoušení prázdný – odvozuje se z posádky). */
  pob_zadany: number | null;
  platce_id: number | null;
  plati_aeroklub: boolean;
  platce_jmeno: string | null;
  platce_prijmeni: string | null;
  poznamka: string | null;
  duvod_zruseni: string | null;
  zruseno: string | null;
  zrusil: string | null;
  dodatecne: boolean;
  zalozeno: string;
  zalozil: string;
  posadka: ClenDetail[];
  tg: string[];
  vlek: { let_id: number; rejstrik: string; pilot: string } | null;
  historie: { kdy: string; kdo: string; akce: string; popis: string | null }[];
  varovani: string | null;
};

export function useDetail(letId: number) {
  return useQuery({
    queryKey: ["let", letId],
    queryFn: () => ziskat<DetailLetu>(`/lety/${letId}`),
    refetchInterval: 10_000,
  });
}
