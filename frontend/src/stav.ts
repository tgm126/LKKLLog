/** Stav dokladu nebo termínu: barva a slovní popis (jednotně v celé aplikaci). */

export const BARVA_STAVU: Record<string, string> = { ok: 'green', info: 'gray', pozor: 'orange', chyba: 'red' }

export const TEXT_STAVU: Record<string, string> = {
  ok: 'v pořádku',
  info: 'v pořádku',
  pozor: 'brzy vyprší',
  chyba: 'neplatné',
}
