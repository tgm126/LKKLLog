/** Práce s časem. Vše se zobrazuje v UTC, jak je v letectví zvykem. */

export const hhmm = (iso: string | Date | null | undefined) =>
  iso ? new Date(iso).toISOString().slice(11, 16) : '–'

export const hhmmss = (iso: string | Date) => new Date(iso).toISOString().slice(11, 19)

/** Doba ve formátu h:mm (např. 1:05). */
export function doba(minuty: number | null | undefined): string {
  if (minuty === null || minuty === undefined) return '–'
  const h = Math.floor(minuty / 60)
  const m = Math.round(minuty % 60)
  return `${h}:${String(m).padStart(2, '0')}`
}

/** Běžící čas od vzletu ve formátu h:mm:ss. */
export function bezi(odIso: string, ted: Date): string {
  const s = Math.max(0, Math.floor((ted.getTime() - new Date(odIso).getTime()) / 1000))
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h}:${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`
}

export const minutOd = (odIso: string, ted: Date) =>
  (ted.getTime() - new Date(odIso).getTime()) / 60000

export const datumCesky = (iso: string) =>
  new Date(`${iso}T12:00:00Z`).toLocaleDateString('cs-CZ', {
    weekday: 'long',
    day: 'numeric',
    month: 'numeric',
    timeZone: 'UTC',
  })

/** Celé minuty bez sekund – pro ručně zadané časy. */
export function naMinuty(d: Date): Date {
  const kopie = new Date(d)
  kopie.setUTCSeconds(0, 0)
  return kopie
}
