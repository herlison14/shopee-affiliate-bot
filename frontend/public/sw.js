// Service worker do ShopeeViral.AI — habilita instalacao como app (PWA).
// Estrategia network-first com cache so de fallback: nunca serve versao velha
// quando ha rede (evita o classico bug de PWA "atualizei e nao mudou nada").
// So intercepta GET de mesma origem (o app no Vercel); chamadas a API (Render,
// outra origem) e metodos != GET passam direto, sem cache.

const CACHE_NAME = 'shopeeviral-v2'

// App shell pre-cacheado no install. Como a SPA usa rotas client-side
// (/dashboard, /vitrine/...), a navegacao offline precisa cair no index.html;
// pre-cachear garante isso mesmo em rotas que o usuario nunca abriu online.
const APP_SHELL = ['/', '/index.html']

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME)
      await cache.addAll(APP_SHELL)
      self.skipWaiting()
    })()
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys()
      await Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
      await self.clients.claim()
    })()
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // So lida com GET de mesma origem; o resto (API cross-origin, POST/PATCH/etc) passa direto.
  if (request.method !== 'GET' || url.origin !== self.location.origin) {
    return
  }

  event.respondWith(
    (async () => {
      try {
        const fresh = await fetch(request)
        // guarda copia no cache pra fallback offline
        const cache = await caches.open(CACHE_NAME)
        cache.put(request, fresh.clone())
        return fresh
      } catch {
        // offline: tenta o cache; se for navegacao, cai no index cacheado
        const cached = await caches.match(request)
        if (cached) return cached
        if (request.mode === 'navigate') {
          // qualquer rota da SPA cai no app shell pre-cacheado
          const shell = (await caches.match('/index.html')) || (await caches.match('/'))
          if (shell) return shell
        }
        throw new Error('offline e sem cache')
      }
    })()
  )
})
