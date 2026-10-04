import type { OsobaVyber } from './api/lety'

export const UROVEN: Record<string, number> = { zak: 0, pilot: 1, instruktor: 2, examinator: 3 }

export type Slot = { funkce: string; popis: string; min: number; max: number }

/** Políčka posádky podle účelu letu (kap. 3.1 návrhu). */
export const SLOTY: Record<string, { pic: Slot; druhy: Slot | null }> = {
  normalni: { pic: { funkce: 'pic', popis: 'PIC', min: 1, max: 3 }, druhy: null },
  vycvik: {
    pic: { funkce: 'pic', popis: 'Instruktor (PIC)', min: 2, max: 3 },
    druhy: { funkce: 'zak', popis: 'Žák', min: 0, max: 0 },
  },
  vycvik_solo: {
    pic: { funkce: 'pic', popis: 'Žák (PIC)', min: 0, max: 0 },
    druhy: { funkce: 'dozor', popis: 'Dozorující instruktor (na zemi)', min: 2, max: 3 },
  },
  prezkouseni: {
    pic: { funkce: 'pic', popis: 'Examinátor / instruktor (PIC)', min: 2, max: 3 },
    druhy: { funkce: 'prezkouseny', popis: 'Přezkoušený pilot', min: 0, max: 3 },
  },
  vlek: { pic: { funkce: 'pic', popis: 'Vlekař (PIC)', min: 1, max: 3 }, druhy: null },
}

/** Vlekař: pilot s oprávněním pro kategorii vlečného letadla. */
export const SLOT_VLEKAR: Slot = { funkce: 'pic', popis: 'Vlekař', min: 1, max: 3 }

export const UCELY = [
  { hodnota: 'normalni', nazev: 'Normální' },
  { hodnota: 'vycvik', nazev: 'Výcvik' },
  { hodnota: 'vycvik_solo', nazev: 'Výcvik sólo' },
  { hodnota: 'prezkouseni', nazev: 'Přezkoušení' },
]

export const KROKY = ['Letadlo', 'Účel', 'Posádka', 'Úloha', 'Vzlet']

export const jmeno = (o: OsobaVyber) => `${o.prijmeni} ${o.jmeno}`

/** Nabídka osob: nahoře ti s odpovídajícím oprávněním, pak ostatní. */
export function nabidka(
  osoby: OsobaVyber[],
  kategorie: string,
  slot: Slot,
  externiSmi: boolean,
  veVzduchu: Set<number>,
) {
  const uroven = (o: OsobaVyber) =>
    Math.max(-1, ...o.opravneni.filter((op) => op.kategorie === kategorie).map((op) => UROVEN[op.uroven]))
  const vhodne = osoby.filter((o) => externiSmi || !o.externi)
  const doporuceni = vhodne
    .filter((o) => uroven(o) >= slot.min && uroven(o) <= slot.max)
    .sort((a, b) => uroven(b) - uroven(a) || jmeno(a).localeCompare(jmeno(b), 'cs'))
  const ostatni = vhodne.filter((o) => !doporuceni.includes(o))
  const polozky = (seznam: OsobaVyber[]) =>
    seznam.map((o) => ({
      value: String(o.id),
      label:
        jmeno(o) + (o.externi ? ' (externí)' : '') + (veVzduchu.has(o.id) ? ' – ✈ ve vzduchu' : ''),
    }))
  return [
    { group: 'Doporučení', items: polozky(doporuceni) },
    { group: 'Ostatní', items: polozky(ostatni) },
  ].filter((g) => g.items.length > 0)
}
