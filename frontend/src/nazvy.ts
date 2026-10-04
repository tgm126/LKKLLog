import type { Ciselniky, Volba } from './api/lety'

const nazev = (volby: Volba[] | undefined, hodnota: string) =>
  volby?.find((v) => v.hodnota === hodnota)?.nazev ?? hodnota

export function useNazvy(c: Ciselniky | undefined) {
  return {
    ucel: (h: string) => nazev(c?.ucely, h),
    funkce: (h: string) => nazev(c?.funkce, h),
    zpusob: (h: string) => nazev(c?.zpusoby_vzletu, h),
    kategorie: (h: string) => nazev(c?.kategorie, h),
    duvod: (h: string) => nazev(c?.duvody_zruseni, h),
  }
}

/** Typ letu = kategorie × účel, např. „Plachtařský · výcvik“. */
export const KATEGORIE_LETU: Record<string, string> = {
  motor: 'Motorový',
  tmg: 'TMG',
  kluzak: 'Plachtařský',
  ul: 'UL',
}
