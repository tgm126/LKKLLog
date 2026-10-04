import { api } from './klient'
import type { Let } from './lety'

export type FiltrVypisu = {
  od: string
  do: string
  letadlo?: string | null
  osoba?: string | null
  platce?: string | null // '0' = aeroklub
  kategorie?: string | null
  ucel?: string | null
  zpusob?: string | null
  soukrome?: boolean
  zrusene?: boolean
}

export type RadekSouhrnu = {
  lety: number
  minuty: number
  tg: number
  navijak: number
  vlek: number
}

export type Souhrn = {
  celkem: RadekSouhrnu
  podle_letadel: (RadekSouhrnu & { imatrikulace: string; typ: string; ucel: string })[]
  podle_platcu: (RadekSouhrnu & { platce: string })[]
  zruseno: number
  neukonceno: number
}

export type Vypis = {
  od: string
  do: string
  lety: Let[]
  souhrn: Souhrn
  smi_exportovat: boolean
}

export function parametry(f: FiltrVypisu): string {
  const p = new URLSearchParams()
  Object.entries(f).forEach(([klic, hodnota]) => {
    if (hodnota === null || hodnota === undefined || hodnota === '' || hodnota === false) return
    p.set(klic, String(hodnota))
  })
  return p.toString()
}

export const nactiVypis = (f: FiltrVypisu) => api<Vypis>(`/vypis?${parametry(f)}`)
export const odkazExportu = (format: 'xlsx' | 'csv', f: FiltrVypisu) =>
  `/api/vypis/export.${format}?${parametry(f)}`
