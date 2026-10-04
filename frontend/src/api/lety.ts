import { api } from './klient'

export type Volba = { hodnota: string; nazev: string }

export type Letadlo = {
  id: number
  imatrikulace: string
  typ: string
  kategorie: string
  pocet_mist: number
  max_doba_min: number | null
  soukrome: boolean
  vlecne: boolean
}

export type OsobaVyber = {
  id: number
  jmeno: string
  prijmeni: string
  externi: boolean
  opravneni: { kategorie: string; uroven: string }[]
}

export type Letiste = {
  id: number
  icao: string | null
  nazev: string
  domovske: boolean
  teren: boolean
}

export type Uloha = { id: number; kod: string; nazev: string; ucely: string[] }
export type Osnova = { id: number; kategorie: string; nazev: string; ulohy: Uloha[] }

export type Ciselniky = {
  letadla: Letadlo[]
  osoby: OsobaVyber[]
  letiste: Letiste[]
  osnovy: Osnova[]
  kategorie: Volba[]
  ucely: Volba[]
  funkce: Volba[]
  zpusoby_vzletu: Volba[]
  duvody_zruseni: Volba[]
  duvody_opravy: Volba[]
  kratke_lety: Volba[]
}

export type Clen = { osoba_id: number; jmeno: string; funkce: string }

export type Let = {
  id: number
  stav: 'pripraven' | 've_vzduchu' | 'ukoncen' | 'zrusen'
  letadlo_id: number
  imatrikulace: string
  typ: string
  kategorie: string
  max_doba_min: number | null
  ucel: string
  uloha: string | null
  uloha_id: number | null
  zpusob_vzletu: string
  posadka: Clen[]
  pocet_hostu: number
  platce: string | null
  platce_id: number | null
  plati_aeroklub: boolean
  misto_vzletu: string
  misto_vzletu_id: number
  misto_pristani: string | null
  misto_pristani_id: number | null
  cas_vzletu: string | null
  cas_pristani: string | null
  doba_min: number | null
  doba_uctovana_min: number | null
  pocet_tg: number
  kratky_let: string
  duvod_zruseni: string
  zalozil: string
  dodatecne: boolean
  verze: number
  muze_ovladat: boolean
}

export type Prehled = {
  den: string
  ted: string
  zapad_slunce: string
  konec_soumraku: string
  lety: Let[]
}

export type NovyLet = {
  letadlo_id: number
  ucel: string
  posadka: { osoba_id: number; funkce: string }[]
  uloha_id: number | null
  zpusob_vzletu: string
  misto_vzletu_id: number | null
  pocet_hostu: number
  platce_id: number | null
  plati_aeroklub: boolean
  akce: 'pripravit' | 'vzlet' | 'dopsat'
  cas_vzletu?: string | null
  cas_pristani?: string | null
  misto_pristani_id?: number | null
  pocet_tg?: number
  kratky_let?: string
}

export type Pristani = {
  cas?: string | null
  misto_pristani_id?: number | null
  pocet_tg: number
  kratky_let?: string
}

export const nactiCiselniky = () => api<Ciselniky>('/ciselniky')
export const nactiPrehled = () => api<Prehled>('/prehled')
export const zalozitLet = (data: NovyLet) => api<Let>('/lety', data)
export const vzlet = (id: number, cas?: string | null) => api<Let>(`/lety/${id}/vzlet`, { cas })
export const pristat = (id: number, data: Pristani) => api<Let>(`/lety/${id}/pristani`, data)
export const zrusitLet = (id: number, duvod: string) =>
  api<Let>(`/lety/${id}/zrusit`, { duvod })

export type Oprava = Omit<NovyLet, 'akce'> & {
  verze: number
  duvod: string
  poznamka: string
}

export type Zaznam = {
  kdy: string
  kdo: string
  akce: string
  zmeny: Record<string, unknown>
  duvod: string
  poznamka: string
}

export const opravitLet = (id: number, data: Oprava) => api<Let>(`/lety/${id}/oprava`, data)
export const vratitZpet = (id: number, verze: number) => api<Let>(`/lety/${id}/zpet`, { verze })
export const nactiHistorii = (id: number) => api<Zaznam[]>(`/lety/${id}/historie`)
