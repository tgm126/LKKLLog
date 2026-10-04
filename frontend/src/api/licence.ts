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
  osoba_id: number
  jmeno: string
  licence: Licence[]
  medicaly: Medical[]
  typy: Volba[]
  /** Které kvalifikace patří ke kterému typu licence. */
  kvalifikace: Record<string, Volba[]>
  tridy: Volba[]
}

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
  posadka: { osoba_id: number; funkce: string }[]
  pocet_hostu: number
  zpusob_vzletu: string
  vlek: { letadlo_id: number; vlekar_id: number } | null
}

/** Bez `osoba` vlastní licence; správce a admin mohou spravovat licence kohokoli. */
const proOsobu = (osoba?: number | null) => (osoba ? `?osoba=${osoba}` : '')

export const nactiLicence = (osoba?: number | null) =>
  api<LicenceStav>(`/ucet/licence${proOsobu(osoba)}`)
export const ulozitLicenci = (data: Omit<Licence, 'id'> & { id?: number }, osoba?: number | null) =>
  api<LicenceStav>(`/ucet/licence${proOsobu(osoba)}`, data)
export const smazatLicenci = (id: number, osoba?: number | null) =>
  api<LicenceStav>(`/ucet/licence/${id}/smazat${proOsobu(osoba)}`, {})
/** Platnost medicalu po třídách; null = třídu nemá. */
export const ulozitMedicalTridy = (tridy: Record<string, string | null>, osoba?: number | null) =>
  api<LicenceStav>(`/ucet/medical/tridy${proOsobu(osoba)}`, { tridy })

export const nactiRozletanost = () => api<Rozletanost>('/nalet/rozletanost')
export const kontrolaPosadky = (data: KontrolaPosadky) =>
  api<{ varovani: string[] }>('/kontrola-posadky', data)

// --- přehled pro správce licencí a letadel ---

export type Pilot = { id: number; jmeno: string; licence: string[]; stav: Kontrola['stav']; problemy: string[] }

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

export const nactiPiloty = () => api<Pilot[]>('/sprava/piloti')
export const nactiPilota = (id: number) => api<Rozletanost>(`/sprava/piloti/${id}`)
export const nactiLetadlaSprava = () => api<LetadloSprava[]>('/sprava/letadla')
export const ulozitDenik = (
  id: number,
  data: { nalet_pocatek_min: number; starty_pocatek: number; stav_k: string | null },
) => api<LetadloSprava[]>(`/sprava/letadla/${id}/denik`, data)
export const ulozitTermin = (data: Omit<Termin, 'id' | 'stav' | 'text'> & { id?: number; letadlo_id: number }) =>
  api<LetadloSprava[]>('/sprava/terminy', data)
export const smazatTermin = (id: number) => api<LetadloSprava[]>(`/sprava/terminy/${id}/smazat`, {})
