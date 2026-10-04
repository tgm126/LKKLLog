import { api } from './klient'
import type { Let } from './lety'

export type RadekNaletu = { lety: number; minuty: number; pristani: number }

export type Nalet = {
  od: string
  do: string
  souhrn: {
    celkem: RadekNaletu
    podle_kategorie: (RadekNaletu & { kategorie: string; funkce: string })[]
    podle_ucelu: (RadekNaletu & { ucel: string })[]
    starty: { kategorie: string; zpusob: string; pocet: number }[]
  }
  /** Nejnovější nahoře; `moje_funkce` = PIC, žák nebo přezkoušený. */
  lety: (Let & { moje_funkce: string })[]
}

const parametry = (od: string, do_: string) => `od=${od}&do=${do_}`

export const nactiNalet = (od: string, do_: string) => api<Nalet>(`/nalet?${parametry(od, do_)}`)
export const odkazExportuNaletu = (od: string, do_: string) =>
  `/api/nalet/export.xlsx?${parametry(od, do_)}`
