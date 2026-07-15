// VEXND SHOP Admin — service worker
// Strategy:
//  - Navigations (HTML): network-first, falls back to cached shell / offline page.
//  - Next.js static assets (/_next/static/...): cache-first (immutable, hashed filenames).
//  - Icons/manifest: cache-first.
//  - API calls (/admin/api/*): always network, never cached (live admin data).

const VERSION = 'v1'
const CACHE_NAME = `vexnd-admin-${VERSION}`
const OFFLINE_URL = '/admin/offline.html'

const PRECACHE_URLS = [
  '/admin',
  OFFLINE_URL,
  '/admin/manifest.webmanifest',
  '/admin/icon-192.png',
  '/admin/icon-512.png',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)).catch(() => {}),
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))),
    ),
  )
  self.clients.claim()
})

function isApiRequest(url) {
  return url.pathname.startsWith('/admin/api/')
}

function isStaticAsset(url) {
  return url.pathname.startsWith('/admin/_next/static/')
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  if (isApiRequest(url)) return // never intercept live admin data

  // App shell / navigation requests: network-first with offline fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => {})
          return response
        })
        .catch(async () => {
          const cached = await caches.match(request)
          return cached || caches.match(OFFLINE_URL)
        }),
    )
    return
  }

  // Hashed static assets: cache-first
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            const copy = response.clone()
            caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => {})
            return response
          }),
      ),
    )
    return
  }

  // Everything else (icons, fonts, manifest): stale-while-revalidate
  event.respondWith(
    caches.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          const copy = response.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy)).catch(() => {})
          return response
        })
        .catch(() => cached)
      return cached || network
    }),
  )
})
