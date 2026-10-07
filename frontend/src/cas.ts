// Čas: vše v UTC (CLAUDE.md, bod 11). „Teď“ podle hodin serveru – hodiny telefonu se mohou
// lišit o desítky sekund a stopky letu musí ukazovat všem totéž.

let posunMs = 0;

/** Zapamatuje si rozdíl mezi časem serveru (z odpovědi) a hodinami zařízení. */
export function nastavitCasServeru(tedServeru: string): void {
  posunMs = new Date(tedServeru).getTime() - Date.now();
}

export function ted(): Date {
  return new Date(Date.now() + posunMs);
}

const dve = (n: number) => String(n).padStart(2, "0");

/** 14:05 (UTC) */
export function hodinyMinuty(cas: string | Date): string {
  const d = new Date(cas);
  return `${dve(d.getUTCHours())}:${dve(d.getUTCMinutes())}`;
}

/** 14:05:09 (UTC) */
export function hodinyMinutySekundy(cas: Date): string {
  return `${hodinyMinuty(cas)}:${dve(cas.getUTCSeconds())}`;
}

/** Stopky letu: 0:12:34 */
export function stopky(odIso: string, do_: Date): string {
  const s = Math.max(0, Math.floor((do_.getTime() - new Date(odIso).getTime()) / 1000));
  return `${Math.floor(s / 3600)}:${dve(Math.floor(s / 60) % 60)}:${dve(s % 60)}`;
}

/** Doba letu leteckým zápisem: 45" pod hodinu, jinak 1°02" */
export function doba(minut: number): string {
  return minut >= 60 ? `${Math.floor(minut / 60)}°${dve(minut % 60)}"` : `${minut}"`;
}

/** 6. 10. 21:14 (UTC) */
export function datumCas(cas: string): string {
  const d = new Date(cas);
  return `${d.getUTCDate()}. ${d.getUTCMonth() + 1}. ${hodinyMinuty(d)}`;
}

/** Úterý 6. 10. 2026 (den ve tvaru RRRR-MM-DD) */
export function denSlovy(den: string): string {
  const d = new Date(`${den}T12:00:00Z`);
  const tyden = d.toLocaleDateString("cs-CZ", { weekday: "long", timeZone: "UTC" });
  return `${tyden.charAt(0).toUpperCase()}${tyden.slice(1)} ${d.getUTCDate()}. ${d.getUTCMonth() + 1}. ${d.getUTCFullYear()}`;
}

/** 6. 10. (den ve tvaru RRRR-MM-DD) */
export function denKratce(den: string): string {
  const d = new Date(`${den}T12:00:00Z`);
  return `${d.getUTCDate()}. ${d.getUTCMonth() + 1}.`;
}
