/** Volání API backendu. Přihlášení nese session cookie, ochranu proti podvrženým
 * požadavkům CSRF token z cookie `csrftoken` (nastaví ho první volání /api/ucet/ja). */

export class ApiChyba extends Error {
  status: number
  /** Strojový kód chyby z backendu (např. `kratky_let`, `uz_zapsano`). */
  kod: string
  letId: number | null

  constructor(status: number, zprava: string, kod = '', letId: number | null = null) {
    super(zprava)
    this.status = status
    this.kod = kod
    this.letId = letId
  }
}

function csrfToken(): string {
  const shoda = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return shoda ? decodeURIComponent(shoda[1]) : ''
}

export async function api<T>(cesta: string, data?: unknown): Promise<T> {
  const odpoved = await fetch(`/api${cesta}`, {
    method: data === undefined ? 'GET' : 'POST',
    credentials: 'same-origin',
    headers: {
      Accept: 'application/json',
      ...(data === undefined ? {} : { 'Content-Type': 'application/json' }),
      'X-CSRFToken': csrfToken(),
    },
    body: data === undefined ? undefined : JSON.stringify(data),
  })
  const telo = await odpoved.json().catch(() => null)
  if (!odpoved.ok) {
    const detail = telo?.detail
    const zprava =
      typeof detail === 'string' ? detail : `Server odpověděl chybou ${odpoved.status}.`
    throw new ApiChyba(odpoved.status, zprava, telo?.kod ?? '', telo?.let_id ?? null)
  }
  return telo as T
}
