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

// --- přehled pro správce licencí a letadel ---

export type Termin = {
  id: number
  nazev: string
  datum: string | null
  pri_naletu_h: number | null
  poznamka: string
  stav: Kontrola['stav']
  text: string
}

export type LetadloSprava = {
  id: number
  imatrikulace: string
  typ: string
  kategorie: string
  nalet_min: number
  starty: number
  nalet_pocatek_min: number
  starty_pocatek: number
  stav_k: string | null
  /** Bez stavu provozního deníku nesedí celkový nálet ani termíny podle náletu. */
  chybi_denik: boolean
  terminy: Termin[]
}

export const nactiLetadlaSprava = () => api<LetadloSprava[]>('/sprava/letadla')
export const ulozitDenik = (
  id: number,
  data: { nalet_pocatek_min: number; starty_pocatek: number; stav_k: string | null },
) => api<LetadloSprava[]>(`/sprava/letadla/${id}/denik`, data)
export const ulozitTermin = (data: Omit<Termin, 'id' | 'stav' | 'text'> & { id?: number; letadlo_id: number }) =>
  api<LetadloSprava[]>('/sprava/terminy', data)
export const smazatTermin = (id: number) => api<LetadloSprava[]>(`/sprava/terminy/${id}/smazat`, {})
