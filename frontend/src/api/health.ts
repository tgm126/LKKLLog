export type Health = {
  status: 'ok' | 'chyba'
  databaze: boolean
  verze: string
}

export async function nactiHealth(): Promise<Health> {
  const odpoved = await fetch('/api/health')
  if (!odpoved.ok) {
    throw new Error(`Server odpověděl ${odpoved.status}`)
  }
  return odpoved.json()
}
