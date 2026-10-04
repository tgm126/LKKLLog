import { api } from './klient'
import type { Let } from './lety'
import type { Souhrn } from './vypis'

/** Let na velkém displeji – jen veřejné údaje a čitelné názvy (displej nemá číselníky). */
export type DisplejLet = Pick<
  Let,
  | 'id'
  | 'stav'
  | 'imatrikulace'
  | 'typ'
  | 'kategorie'
  | 'max_doba_min'
  | 'ucel'
  | 'zpusob_vzletu'
  | 'pocet_hostu'
  | 'misto_vzletu'
  | 'misto_pristani'
  | 'cas_vzletu'
  | 'cas_pristani'
  | 'doba_uctovana_min'
  | 'pocet_tg'
  | 'casy_tg'
  | 'pocet_pristani'
  | 'duvod_zruseni'
  | 'vlek_id'
  | 'vlek'
> & {
  ucel_nazev: string
  zpusob_nazev: string
  posadka: { jmeno: string; funkce: string; funkce_nazev: string }[]
}

export type Displej = {
  den: string
  ted: string
  zapad_slunce: string
  konec_soumraku: string
  lety: DisplejLet[]
  souhrn: Souhrn
}

export const nactiDisplej = (klic: string) =>
  api<Displej>(`/displej?klic=${encodeURIComponent(klic)}`)
