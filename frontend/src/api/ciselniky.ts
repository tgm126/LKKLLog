import { api } from './klient'

/** Správa číselníků (jen admin): seznamy hodnot, na které se odkazují karty. */

export type PoleCiselniku = {
  klic: string
  nazev: string
  typ: 'text' | 'cislo' | 'bool' | 'volba' | 'vice'
  volby: [string, string][]
}

export type RadekCiselniku = { id: number; systemova: boolean; hodnoty: Record<string, unknown> }

export type Ciselnik = {
  klic: string
  nazev: string
  popis: string
  deti: string | null
  pole: PoleCiselniku[]
  radky: RadekCiselniku[]
}

export type PrehledCiselniku = {
  klic: string
  nazev: string
  popis: string
  rodic: boolean
  /** Klíč podřízeného číselníku (kvalifikace pod průkazem, úlohy pod osnovou). */
  deti: string | null
  pocet: number
}

const URL = '/sprava/ciselniky'

export const nactiSeznamCiselniku = () => api<PrehledCiselniku[]>(URL)
export const nactiCiselnik = (klic: string, rodic?: number | null) =>
  api<Ciselnik>(`${URL}/${klic}${rodic ? `?rodic=${rodic}` : ''}`)
export const ulozitPolozku = (
  klic: string,
  data: { id?: number; rodic?: number | null; hodnoty: Record<string, unknown> },
) => api<Ciselnik>(`${URL}/${klic}`, data)
export const smazatPolozku = (klic: string, id: number) => api<Ciselnik>(`${URL}/${klic}/${id}/smazat`, {})
