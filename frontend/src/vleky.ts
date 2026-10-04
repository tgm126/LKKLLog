import type { Let } from './api/lety'

/** Rozdělí lety na samostatné a dvojice vleku (kluzák + vlečná), pokud jsou obě v seznamu. */
export function seskupitVleky(lety: Let[]): (Let | [Let, Let])[] {
  const vysledek: (Let | [Let, Let])[] = []
  const hotove = new Set<number>()
  for (const l of lety) {
    if (hotove.has(l.id)) continue
    const druhy = l.vlek_id ? lety.find((x) => x.id === l.vlek_id) : undefined
    if (druhy) {
      // Kluzák nahoře, vlečná pod ním.
      vysledek.push(l.zpusob_vzletu === 'vlek' ? [l, druhy] : [druhy, l])
      hotove.add(druhy.id)
    } else {
      vysledek.push(l)
    }
    hotove.add(l.id)
  }
  return vysledek
}
