import type { OsobaVyber } from './api/lety'

/** Kdo se do políčka doporučí (podle průkazů, výcviku a přeškolení, viz osoby/nabidky.py). */
export type Kdo = 'pilot' | 'instruktor' | 'examinator' | 'zak' | 'dozor' | 'vlekar'

export type Slot = { funkce: string; popis: string; kdo: Kdo }

/** Políčka posádky podle účelu letu (kap. 3.1 návrhu). */
export const SLOTY: Record<string, { pic: Slot; druhy: Slot | null }> = {
  normalni: { pic: { funkce: 'pic', popis: 'PIC', kdo: 'pilot' }, druhy: null },
  vycvik: {
    pic: { funkce: 'pic', popis: 'Instruktor (PIC)', kdo: 'instruktor' },
    druhy: { funkce: 'zak', popis: 'Žák', kdo: 'zak' },
  },
  vycvik_solo: {
    pic: { funkce: 'pic', popis: 'Žák (PIC)', kdo: 'zak' },
    druhy: { funkce: 'dozor', popis: 'Dozorující instruktor (na zemi)', kdo: 'dozor' },
  },
  prezkouseni: {
    pic: { funkce: 'pic', popis: 'Examinátor / instruktor (PIC)', kdo: 'examinator' },
    druhy: { funkce: 'prezkouseny', popis: 'Přezkoušený pilot', kdo: 'pilot' },
  },
  vlek: { pic: { funkce: 'pic', popis: 'Vlekař (PIC)', kdo: 'vlekar' }, druhy: null },
}

/** Vlekař: pilot s kvalifikací vlekání pro kategorii vlečného letadla. */
export const SLOT_VLEKAR: Slot = { funkce: 'pic', popis: 'Vlekař', kdo: 'vlekar' }

export const UCELY = [
  { hodnota: 'normalni', nazev: 'Normální' },
  { hodnota: 'vycvik', nazev: 'Výcvik' },
  { hodnota: 'vycvik_solo', nazev: 'Výcvik sólo' },
  { hodnota: 'prezkouseni', nazev: 'Přezkoušení' },
]

export const KROKY = ['Letadlo', 'Účel', 'Posádka', 'Úloha', 'Vzlet']

export const jmeno = (o: OsobaVyber) => `${o.prijmeni} ${o.jmeno}`

export type PolozkaOsoby = { value: string; label: string }

/** Nabídka osob rozdělená na doporučené a ostatní.
 *
 * Doporučí se podle karty osoby: PIC a vlekař = průkaz (kvalifikace) pro kategorii
 * a přeškolení na typ letadla; instruktor, dozor, examinátor, žák = osvědčení a výcvik.
 */
export function nabidka(
  osoby: OsobaVyber[],
  letadlo: { kategorie: string; typ_letadla_id: number | null },
  slot: Slot,
  externiSmi: boolean,
  veVzduchu: Set<number>,
): { doporuceni: PolozkaOsoby[]; ostatni: PolozkaOsoby[] } {
  const kat = letadlo.kategorie
  // Letadlo bez typu z číselníku přeškolení nekontroluje.
  const preskolen = (o: OsobaVyber) => !letadlo.typ_letadla_id || o.typy.includes(letadlo.typ_letadla_id)
  const vhodny = (o: OsobaVyber) => {
    switch (slot.kdo) {
      case 'pilot':
        return o.pilot.includes(kat) && preskolen(o)
      case 'vlekar':
        return o.vlekar.includes(kat) && preskolen(o)
      case 'instruktor':
        return o.instruktor.includes(kat)
      case 'examinator':
        return o.examinator.includes(kat) || o.instruktor.includes(kat)
      case 'dozor':
        return o.dozor.includes(kat)
      case 'zak':
        return o.zak.includes(kat)
    }
  }
  const vhodne = osoby.filter((o) => externiSmi || !o.externi)
  const doporuceni = vhodne.filter(vhodny).sort((a, b) => jmeno(a).localeCompare(jmeno(b), 'cs'))
  const ostatni = vhodne.filter((o) => !doporuceni.includes(o))
  const polozky = (seznam: OsobaVyber[]) =>
    seznam.map((o) => ({
      value: String(o.id),
      label:
        jmeno(o) + (o.externi ? ' (externí)' : '') + (veVzduchu.has(o.id) ? ' – ✈ ve vzduchu' : ''),
    }))
  return { doporuceni: polozky(doporuceni), ostatni: polozky(ostatni) }
}
