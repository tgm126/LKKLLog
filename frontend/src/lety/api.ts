// Data letů ze serveru (backend/app/lety.py).
import { useQuery } from "@tanstack/react-query";

import { ziskat, type Schemata } from "../api";
import { nastavitCasServeru } from "../cas";

export type Den = Schemata["Den"];
export type Clen = Schemata["Clen"];
export type Pasek = Schemata["Pasek"];
export type Stav = Pasek["stav"];

/** Dotaz na den: bez dne dnešek, jinak `?den=RRRR-MM-DD` (desktop – jiný den). */
const sDnem = (cesta: string, den?: string) => (den ? `${cesta}?den=${den}` : cesta);

/** Den do hlavičky (datum, sluneční časy); jednou za minutu kvůli přechodu půlnoci. */
export function useDen(den?: string) {
  return useQuery({
    queryKey: ["den", den ?? "dnes"],
    queryFn: async () => {
      const d = await ziskat<Den>(sDnem("/den", den));
      nastavitCasServeru(d.ted);
      return d;
    },
    refetchInterval: 60_000,
  });
}

/** Lety dne; obnovují se samy každých 10 s a po návratu do aplikace (docs/modul-lety.md 3.2).
 *  Bez dne dnešek (i vše, co je ve vzduchu), jinak lety zvoleného dne (desktop). */
export type RadekSouhrnu = Schemata["RadekSouhrnu"];
type LetyDne = Schemata["LetyDne"];

/** Lety dne a souhrn jedním dotazem (obnoví se spolu); každý háček vybere svou část.
 *  Moje = jen lety, kde jsem v posádce (docs/modul-moje-lety.md). */
function useLetyDne<T>(den: string | undefined, vybrat: (d: LetyDne) => T, moje = false) {
  return useQuery({
    queryKey: ["lety", den ?? "dnes", ...(moje ? ["moje"] : [])],
    queryFn: async () => {
      const cesta = sDnem("/lety", den);
      const lety = await ziskat<LetyDne>(moje ? `${cesta}${den ? "&" : "?"}moje=true` : cesta);
      nastavitCasServeru(lety.ted);
      return lety;
    },
    select: vybrat,
    refetchInterval: 10_000,
  });
}

const jenLety = (d: LetyDne) => d.lety;
const jenSouhrn = (d: LetyDne) => d.souhrn;

export function useLety(den?: string, moje = false) {
  return useLetyDne(den, jenLety, moje);
}

/** Dny, kdy mám nějaký let (RRRR-MM-DD, vzestupně) – šipky v Moje lety. */
export function useMojeDny() {
  return useQuery({
    queryKey: ["lety", "moje-dny"],
    queryFn: () => ziskat<string[]>("/lety/moje-dny"),
  });
}

export function useSouhrnDne(den?: string) {
  return useLetyDne(den, jenSouhrn);
}

// --- průvodce novým letem --------------------------------------------------------------------

export type LetadloNabidka = Schemata["LetadloNabidky"];
export type Funkce = Schemata["Funkce"];
export type Ucel = Schemata["UcelNabidky"];
export type Role = Schemata["Role"];
export type Osoba = Schemata["OsobaNabidky"];
export type Prezkouseni = Schemata["PrezkouseniNabidky"];
export type Uloha = Schemata["UlohaNabidky"];
export type Nabidky = Schemata["Nabidky"];

export function useNabidky() {
  return useQuery({
    queryKey: ["nabidky"],
    queryFn: () => ziskat<Nabidky>("/lety/nabidky"),
    staleTime: 0,
  });
}

// --- detail letu -----------------------------------------------------------------------------

export type ClenDetail = Schemata["ClenDetail"];
export type DetailLetu = Schemata["DetailLetu"];

export function useDetail(letId: number) {
  return useQuery({
    queryKey: ["let", letId],
    queryFn: () => ziskat<DetailLetu>(`/lety/${letId}`),
    refetchInterval: 10_000,
  });
}
