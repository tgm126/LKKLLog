import { api } from './klient'

/** Push upozornění na tomto zařízení (Web Push přes service worker /sw.js). */

type Stav = { klic: string; zarizeni: number }

export const nactiStavPush = () => api<Stav>('/ucet/push')
export const zkusebniPush = () => api<{ pocet: number }>('/ucet/push/zkouska', {})

export const pushPodporovan = () =>
  'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window

export const jeIos = () => /iPad|iPhone|iPod/.test(navigator.userAgent)

/** Aplikace spuštěná z plochy (na iPhonu jen tak fungují upozornění). */
export const jeNaPlose = () =>
  window.matchMedia('(display-mode: standalone)').matches ||
  (navigator as Navigator & { standalone?: boolean }).standalone === true

export function registrovatServiceWorker() {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {
      // Bez service workeru jen nefungují upozornění; aplikace jede dál.
    })
  }
}

export async function odberZarizeni(): Promise<PushSubscription | null> {
  const registrace = await navigator.serviceWorker.getRegistration()
  return registrace ? registrace.pushManager.getSubscription() : null
}

function klicNaBajty(klic: string): Uint8Array<ArrayBuffer> {
  const base64 = (klic + '='.repeat((4 - (klic.length % 4)) % 4)).replace(/-/g, '+').replace(/_/g, '/')
  const surovy = atob(base64)
  const bajty = new Uint8Array(new ArrayBuffer(surovy.length))
  for (let i = 0; i < surovy.length; i++) bajty[i] = surovy.charCodeAt(i)
  return bajty
}

function popisZarizeni(): string {
  const ua = navigator.userAgent
  const system = /iPhone|iPad/.test(ua)
    ? 'iPhone/iPad'
    : /Android/.test(ua)
      ? 'Android'
      : /Windows/.test(ua)
        ? 'Windows'
        : /Mac/.test(ua)
          ? 'Mac'
          : 'jiné'
  const prohlizec = /Edg\//.test(ua)
    ? 'Edge'
    : /Firefox\//.test(ua)
      ? 'Firefox'
      : /Chrome\//.test(ua)
        ? 'Chrome'
        : /Safari\//.test(ua)
          ? 'Safari'
          : ''
  return `${system} ${prohlizec}`.trim()
}

export async function zapnoutPush(klic: string): Promise<Stav> {
  const povoleni = await Notification.requestPermission()
  if (povoleni !== 'granted') {
    throw new Error('Upozornění jsou v prohlížeči zakázaná. Povolte je v nastavení prohlížeče.')
  }
  const registrace = await navigator.serviceWorker.ready
  // Starý odběr (např. s jiným klíčem serveru) nejdřív zrušíme.
  await (await registrace.pushManager.getSubscription())?.unsubscribe()
  const odber = await registrace.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: klicNaBajty(klic),
  })
  const json = odber.toJSON()
  return api<Stav>('/ucet/push', {
    endpoint: json.endpoint,
    keys: json.keys,
    zarizeni: popisZarizeni(),
  })
}

export async function vypnoutPush(): Promise<Stav> {
  const odber = await odberZarizeni()
  const stav = await api<Stav>('/ucet/push/vypnout', { endpoint: odber?.endpoint ?? '' })
  await odber?.unsubscribe()
  return stav
}
