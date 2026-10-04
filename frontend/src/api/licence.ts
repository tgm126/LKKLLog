import { api } from './klient'

export type Kontrola = {
  /** Modul hlídání: způsobilost (doklady), nebo rozlétanost (nálet za období). */
  modul: 'zpusobilost' | 'rozletanost'
  oblast: string
  nazev: string
  stav: 'ok' | 'pozor' | 'chyba' | 'info'
  text: string
  plati_do: string | null
  podrobnosti: string[]
}

export type Rozletanost = {
  moduly: { zpusobilost: boolean; rozletanost: boolean }
  zobrazit: boolean
  kontroly: Kontrola[]
}

export type KontrolaPosadky = {
  letadlo_id: number
  ucel: string
  posadka: { osoba_id: number; funkce: string }[]
  pocet_hostu: number
  zpusob_vzletu: string
  vlek: { letadlo_id: number; vlekar_id: number } | null
}

export const nactiRozletanost = () => api<Rozletanost>('/nalet/rozletanost')
export const kontrolaPosadky = (data: KontrolaPosadky) =>
  api<{ varovani: string[] }>('/kontrola-posadky', data)
