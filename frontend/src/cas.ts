/** Práce s časem. Vše se zobrazuje v UTC, jak je v letectví zvykem. */

export const hhmm = (iso: string | Date | null | undefined) =>
  iso ? new Date(iso).toISOString().slice(11, 16) : '–'

export const hhmmss = (iso: string | Date) => new Date(iso).toISOString().slice(11, 19)

/** Doba v leteckém zápisu: 1°4" = hodina a čtyři minuty, 10" = deset minut (bez 0°). */
export function doba(minuty: number | null | undefined): string {
  if (minuty === null || minuty === undefined) return '–'
  const celkem = Math.round(minuty)
  const hodiny = Math.floor(celkem / 60)
  return hodiny > 0 ? `${hodiny}°${celkem % 60}"` : `${celkem}"`
}

/** Běžící čas od vzletu: letecký zápis hodin a minut + sekundy zvlášť. */
export function bezi(odIso: string, ted: Date): { cas: string; sekundy: string } {
  const s = Math.max(0, Math.floor((ted.getTime() - new Date(odIso).getTime()) / 1000))
  return { cas: doba(Math.floor(s / 60)), sekundy: String(s % 60).padStart(2, '0') }
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
