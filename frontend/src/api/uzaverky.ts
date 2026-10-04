import { api } from './klient'
import type { Souhrn } from './vypis'

export type TypUzaverky = 'den' | 'mesic'

export type Uzaverka = {
  id: number
  typ: TypUzaverky
  obdobi: string
  verze: number
  kdy: string
  uzavrel: string
  platna: boolean
}

/** Stav uzávěrky dne v přehledu dne. */
export type StavDne = {
  uzaverka: Uzaverka | null
  mesic_uzavren: boolean
  zmeny: number
  smi_uzavrit: boolean
}

export type DenMesice = {
  den: string
  lety: number
  minuty: number
  neukonceno: number
  uzaverka: Uzaverka | null
  zmeny: number
  smi_uzavrit: boolean
}

export type Mesic = {
  mesic: string
  dny: DenMesice[]
  uzaverka: Uzaverka | null
  zmeny: number
  skoncil: boolean
  smi_uzavrit: boolean
}

export type SouhrnUzaverky = Souhrn & {
  starty: Record<string, number>
  podle_osob: { osoba_id: number; osoba: string; funkce: string; lety: number; minuty: number }[]
  soukrome: { lety: number; minuty: number }
}

export type Nahled = {
  typ: TypUzaverky
  obdobi: string
  souhrn: SouhrnUzaverky
  lze: boolean
  zakaz: string | null
  neukonceno: string[]
  neuzavrene_dny: string[]
  posledni: Uzaverka | null
  /** Uzavírá se dnešní den. */
  dnes: boolean
}

export type ZmenenyLet = {
  id: number
  imatrikulace: string
  cas_vzletu: string | null
  cas_pristani: string | null
  stav: string
  doba_uctovana_min: number | null
  zaznamy: {
    kdy: string
    kdo: string
    akce: string
    zmeny: Record<string, unknown>
    duvod: string
    poznamka: string
  }[]
}

export type DetailUzaverky = {
  typ: TypUzaverky
  obdobi: string
  verze: Uzaverka[]
  souhrn: SouhrnUzaverky | null
  rozdil: { celkem: Record<string, number>; starty: Record<string, number> } | null
  lety: ZmenenyLet[]
}

export const nactiMesic = (mesic: string) => api<Mesic>(`/uzaverky?mesic=${mesic}`)
export const nactiNahled = (typ: TypUzaverky, obdobi: string) =>
  api<Nahled>(`/uzaverky/nahled?typ=${typ}&obdobi=${obdobi}`)
export const nactiDetail = (typ: TypUzaverky, obdobi: string) =>
  api<DetailUzaverky>(`/uzaverky/detail?typ=${typ}&obdobi=${obdobi}`)
export const uzavrit = (typ: TypUzaverky, obdobi: string) =>
  api<Uzaverka>('/uzaverky', { typ, obdobi })
export const odkazExportuUzaverky = (id: number) => `/api/uzaverky/${id}/export.xlsx`
