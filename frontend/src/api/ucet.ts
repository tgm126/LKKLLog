import { api } from './klient'

export type Ja = {
  prihlasen: boolean
  id: number | null
  jmeno: string
  prijmeni: string
  email: string | null
  role: { admin: boolean; casomeric: boolean; ucetni: boolean; spravce: boolean } | null
  zastupce: { id: number; jmeno: string } | null
  testovaci_provoz: boolean
}

type Zprava = { zprava: string }

export const nactiJa = () => api<Ja>('/ucet/ja')
export const prihlasit = (email: string, heslo: string, zapamatovat: boolean) =>
  api<Ja>('/ucet/prihlasit', { email, heslo, zapamatovat })
export const odhlasit = () => api<Ja>('/ucet/odhlasit', {})
export const vratitSe = () => api<Ja>('/ucet/vratit-se', {})
export const zapomenuteHeslo = (email: string) => api<Zprava>('/ucet/zapomenute-heslo', { email })
export const overitOdkaz = (uid: string, token: string) =>
  api<Zprava>(`/ucet/nastavit-heslo/${uid}/${token}`)
export const nastavitHeslo = (uid: string, token: string, heslo: string) =>
  api<Ja>('/ucet/nastavit-heslo', { uid, token, heslo })
