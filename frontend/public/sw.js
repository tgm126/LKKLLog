// Service worker LKKL Log: jen zobrazuje push upozornění (žádné ukládání stránek offline).

self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (udalost) => udalost.waitUntil(self.clients.claim()))

self.addEventListener('push', (udalost) => {
  let data = {}
  try {
    data = udalost.data ? udalost.data.json() : {}
  } catch {
    data = { text: udalost.data ? udalost.data.text() : '' }
  }
  udalost.waitUntil(
    self.registration.showNotification(data.titulek || 'LKKL Log', {
      body: data.text || '',
      // Stejná značka nahradí starší upozornění téhož druhu k témuž letu.
      tag: data.znacka || undefined,
      icon: '/ikona-192.png',
      badge: '/ikona-192.png',
      lang: 'cs',
      data: { url: data.url || '/' },
    }),
  )
})

// Ťuknutí na upozornění otevře aplikaci (nebo přepne do už otevřené).
self.addEventListener('notificationclick', (udalost) => {
  udalost.notification.close()
  const url = (udalost.notification.data && udalost.notification.data.url) || '/'
  udalost.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((okna) => {
      for (const okno of okna) {
        if ('focus' in okno) return okno.focus()
      }
      return self.clients.openWindow(url)
    }),
  )
})
