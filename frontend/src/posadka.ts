import type { OsobaVyber } from './api/lety'

/** Úrovně oprávnění v kategorii; vlekař je příznak, ale znamená i pilota. */
export const UROVEN: Record<string, number> = { zak: 0, pilot: 1, vlekar: 1, instruktor: 2, examinator: 3 }

/** Políčko posádky: kdo se doporučí (rozsah úrovní, případně jen vlekaři). */
export type Slot = { funkce: string; popis: string; min: number; max: number; vlekar?: boolean }

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
  vlek: { pic: { funkce: 'pic', popis: 'Vlekař (PIC)', min: 1, max: 3, vlekar: true }, druhy: null },
}

/** Vlekař: pilot s příznakem vlekař pro kategorii vlečného letadla. */
export const SLOT_VLEKAR: Slot = { funkce: 'pic', popis: 'Vlekař', min: 1, max: 3, vlekar: true }

export const UCELY = [
  { hodnota: 'normalni', nazev: 'Normální' },
  { hodnota: 'vycvik', nazev: 'Výcvik' },
  { hodnota: 'vycvik_solo', nazev: 'Výcvik sólo' },
  { hodnota: 'prezkouseni', nazev: 'Přezkoušení' },
]

export const KROKY = ['Letadlo', 'Účel', 'Posádka', 'Úloha', 'Vzlet']

export const jmeno = (o: OsobaVyber) => `${o.prijmeni} ${o.jmeno}`

export type PolozkaOsoby = { value: string; label: string }

/** Nabídka osob rozdělená na doporučené (podle oprávnění) a ostatní. */
export function nabidka(
  osoby: OsobaVyber[],
  kategorie: string,
  slot: Slot,
  externiSmi: boolean,
  veVzduchu: Set<number>,
): { doporuceni: PolozkaOsoby[]; ostatni: PolozkaOsoby[] } {
  const opravneni = (o: OsobaVyber) => o.opravneni.filter((op) => op.kategorie === kategorie)
  const uroven = (o: OsobaVyber) => Math.max(-1, ...opravneni(o).map((op) => UROVEN[op.uroven] ?? -1))
  const vhodny = (o: OsobaVyber) =>
    slot.vlekar
      ? opravneni(o).some((op) => op.uroven === 'vlekar')
      : uroven(o) >= slot.min && uroven(o) <= slot.max
  const vhodne = osoby.filter((o) => externiSmi || !o.externi)
  const doporuceni = vhodne
    .filter(vhodny)
    .sort((a, b) => uroven(b) - uroven(a) || jmeno(a).localeCompare(jmeno(b), 'cs'))
  const ostatni = vhodne.filter((o) => !doporuceni.includes(o))
  const polozky = (seznam: OsobaVyber[]) =>
    seznam.map((o) => ({
      value: String(o.id),
      label:
        jmeno(o) + (o.externi ? ' (externí)' : '') + (veVzduchu.has(o.id) ? ' – ✈ ve vzduchu' : ''),
    }))
  return { doporuceni: polozky(doporuceni), ostatni: polozky(ostatni) }
}
