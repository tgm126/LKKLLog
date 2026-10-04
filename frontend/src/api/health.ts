import { api } from './klient'

export type Health = {
  status: 'ok' | 'chyba'
  databaze: boolean
  verze: string
}

export const nactiHealth = () => api<Health>('/health')
