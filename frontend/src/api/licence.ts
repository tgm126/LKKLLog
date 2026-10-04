import { api } from './klient'

export type Volba = { hodnota: string; nazev: string }
export type KvalifikaceData = { druh: string; platnost_do: string | null }

export type Licence = {
  id: number
  typ: string
  cislo: string
  poznamka: string
  kvalifikace: KvalifikaceData[]
}

export type Medical = { id: number; trida: string; platnost_do: string }

export type LicenceStav = {
  licence: Licence[]
  medicaly: Medical[]
  typy: Volba[]
  /** Které kvalifikace patří ke kterému typu licence. */
  kvalifikace: Record<string, Volba[]>
  tridy: Volba[]
}

export type Kontrola = {
  oblast: string
  nazev: string
  stav: 'ok' | 'pozor' | 'chyba' | 'info'
  text: string
  plati_do: string | null
  podrobnosti: string[]
}

export type Rozletanost = { hlidani: boolean; zobrazit: boolean; kontroly: Kontrola[] }

export type KontrolaPosadky = {
  letadlo_id: number
  posadka: { osoba_id: number; funkce: string }[]
  pocet_hostu: number
  zpusob_vzletu: string
  vlek: { letadlo_id: number; vlekar_id: number } | null
}

export const nactiLicence = () => api<LicenceStav>('/ucet/licence')
export const ulozitLicenci = (data: Omit<Licence, 'id'> & { id?: number }) =>
  api<LicenceStav>('/ucet/licence', data)
export const smazatLicenci = (id: number) => api<LicenceStav>(`/ucet/licence/${id}/smazat`, {})
export const ulozitMedical = (data: Omit<Medical, 'id'> & { id?: number }) =>
  api<LicenceStav>('/ucet/medical', data)
export const smazatMedical = (id: number) => api<LicenceStav>(`/ucet/medical/${id}/smazat`, {})

export const nactiRozletanost = () => api<Rozletanost>('/nalet/rozletanost')
export const kontrolaPosadky = (data: KontrolaPosadky) =>
  api<{ varovani: string[] }>('/kontrola-posadky', data)
