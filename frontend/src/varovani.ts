import type { Let } from './api/lety'
import { doba, minutOd } from './cas'

/** Varování u letu ve vzduchu: přes maximální dobu letadla nebo po konci soumraku. */
export function varovani(
  let_: Pick<Let, 'stav' | 'cas_vzletu' | 'max_doba_min'>,
  ted: Date,
  konecSoumraku: string,
): string | null {
  if (let_.stav !== 've_vzduchu' || !let_.cas_vzletu) return null
  if (let_.max_doba_min && minutOd(let_.cas_vzletu, ted) > let_.max_doba_min) {
    return `Déle než max. doba letu (${doba(let_.max_doba_min)}) – nezapomněl někdo přistání?`
  }
  if (ted > new Date(konecSoumraku)) return 'Po konci občanského soumraku a stále ve vzduchu.'
  return null
}
