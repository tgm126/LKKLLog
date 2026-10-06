// Data letů ze serveru (backend/app/lety.py).
import { useQuery } from "@tanstack/react-query";

import { ziskat } from "../api";
import { nastavitCasServeru } from "../cas";

export type Den = {
  den: string;
  ted: string;
  domovske: string | null;
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
  pob: number | null;
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
export type Osoba = { id: number; jmeno: string; prijmeni: string; vlekar: boolean };
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
