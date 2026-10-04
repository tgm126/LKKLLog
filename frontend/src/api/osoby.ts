import { api } from './klient'
import type { Kontrola } from './licence'

/** Osoby a jejich karty (admin, správce licencí a letadel). */

export type RadekOsoby = {
  id: number
  jmeno: string
  email: string | null
  aktivni: boolean
  externi: boolean
  testovaci: boolean
  role: string[]
  prukazy: string[]
  /** ok / info / pozor / chyba, prázdné = nelétá */
  stav: '' | Kontrola['stav']
  problemy: string[]
}

export type KvalifikaceData = { kvalifikace_id: number; platnost_do: string | null }
export type PrukazData = { druh_id: number; cislo: string; poznamka: string; kvalifikace: KvalifikaceData[] }
export type VycvikData = {
  druh_id: number
  zahajen: string | null
  solo_povoleno: string | null
  ukoncen: string | null
  poznamka: string
}
export type Role = { casomeric: boolean; ucetni: boolean; spravce: boolean; admin: boolean }

export type Karta = {
  id: number
  jmeno: string
  prijmeni: string
  email: string | null
  ma_telefon: boolean
  aktivni: boolean
  externi: boolean
  testovaci: boolean
  role: Role
  prukazy: PrukazData[]
  provozni: number[]
  preskoleni: number[]
  vycviky: VycvikData[]
  kontroly: Kontrola[]
}

/** Data k uložení; telefon jen když se načetl a změnil (jinak se nemění). */
export type KartaIn = Omit<Karta, 'id' | 'ma_telefon' | 'kontroly'> & { telefon?: string | null }

export type VolbaKvalifikace = { id: number; nazev: string; ma_platnost: boolean; aktivni: boolean }
export type VolbaDruhu = {
  id: number
  nazev: string
  skupina: 'pilotni' | 'instruktor' | 'examinator' | 'medical' | 'radio' | 'jazyk'
  aktivni: boolean
  kvalifikace: VolbaKvalifikace[]
}
export type Volby = {
  druhy: VolbaDruhu[]
  provozni: { id: number; nazev: string; aktivni: boolean }[]
  typy: { id: number; nazev: string; kategorie: string; aktivni: boolean }[]
}

const URL = '/sprava/osoby'

export const nactiOsoby = () => api<RadekOsoby[]>(URL)
export const nactiVolbyOsob = () => api<Volby>(`${URL}/volby`)
export const nactiKartu = (id: number) => api<Karta>(`${URL}/${id}`)
export const nactiTelefon = (id: number) => api<{ telefon: string }>(`${URL}/${id}/telefon`)
export const ulozitKartu = (id: number | null, data: KartaIn) =>
  api<Karta>(id ? `${URL}/${id}` : URL, data)
