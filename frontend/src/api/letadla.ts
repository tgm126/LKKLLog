import { api } from './klient'
import type { Kontrola } from './licence'

/** Letadla a jejich karty (admin, správce licencí a letadel). */

export const KATEGORIE_LETADLA: Record<string, string> = {
  motor: 'Motorové',
  tmg: 'TMG',
  kluzak: 'Kluzák',
  ul: 'UL',
}

/** Termín k uložení: datum, nebo celkový nálet [h] (při obou platí, co nastane dřív). */
export type TerminData = {
  druh_id: number
  datum: string | null
  pri_naletu_h: number | null
  poznamka: string
}

export type Termin = TerminData & {
  id: number
  nazev: string
  stav: Kontrola['stav']
  text: string
}

export type KartaLetadlaIn = {
  imatrikulace: string
  typ_letadla_id: number | null
  pocet_mist: number
  max_doba_min: number | null
  vlecne: boolean
  soukrome: boolean
  aktivni: boolean
  poradi: number
  nalet_pocatek_min: number
  starty_pocatek: number
  stav_k: string | null
  terminy: TerminData[]
}

export type KartaLetadla = Omit<KartaLetadlaIn, 'terminy'> & {
  id: number
  typ: string
  kategorie: string
  nalet_min: number
  starty: number
  /** Bez stavu provozního deníku nesedí celkový nálet ani termíny podle náletu. */
  chybi_denik: boolean
  terminy: Termin[]
}

export type VolbyLetadel = {
  typy: { id: number; nazev: string; kategorie: string; aktivni: boolean }[]
  druhy_terminu: { id: number; nazev: string; aktivni: boolean }[]
}

const URL = '/sprava/letadla'

export const nactiLetadla = (vse: boolean) => api<KartaLetadla[]>(vse ? `${URL}?vse=true` : URL)
export const nactiVolbyLetadel = () => api<VolbyLetadel>(`${URL}/volby`)
export const nactiKartuLetadla = (id: number) => api<KartaLetadla>(`${URL}/${id}`)
export const ulozitKartuLetadla = (id: number | null, data: KartaLetadlaIn) =>
  api<KartaLetadla>(id ? `${URL}/${id}` : URL, data)
