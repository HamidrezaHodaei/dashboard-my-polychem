/* Polychem service worker.
 *
 * Scope of caching -- deliberately small:
 *   - the offline page and the app icons (precache)
 *   - build-hashed static assets under /_nuxt/ and /_fonts/ (cache-first: the URL changes with the content)
 *   - icons, splash images, manifest, the favicon (stale-while-revalidate)
 *
 * NEVER cached or even intercepted: anything that is not a same-origin GET, API calls (/api, /backend),
 * requests carrying an Authorization header, Range requests (file downloads / media), and any response that
 * is not a plain 200. The access token lives in memory and the refresh cookie is HttpOnly on the API origin, so
 * there is no private data this worker could ever see or store -- and it must stay that way.
 *
 * Navigations are network-first; with no network the user gets /offline.html. (The SPA shell is not served
 * from cache on purpose: without the API the panel cannot show anything, and a stale shell referencing
 * deleted /_nuxt chunks is the classic way an installed app breaks after a deploy.)
 *
 * Push: the worker also receives Web Push messages (see the push / notificationclick handlers at the end). The payload
 * is encrypted for this device by the push protocol and contains only what the user allowed (see backend push.py).
 *
 * Updates: a new worker installs and WAITS. The page shows an "update available" bar and sends SKIP_WAITING when
 * the user accepts, so a form in progress is never reloaded under the user. Bump VERSION on every deploy that
 * changes this file's behaviour (the file itself is served with Cache-Control: no-cache, see PWA.md).
 */
const VERSION = 'v2'
const STATIC_CACHE = `polychem-static-${VERSION}`
const RUNTIME_CACHE = `polychem-runtime-${VERSION}`
const OFFLINE_URL = '/offline.html'
const PRECACHE = [OFFLINE_URL, '/icons/icon-192.png', '/icons/icon-512.png', '/icons/apple-touch-icon.png']
const PRIVATE_PREFIXES = ['/api/', '/backend/']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => cache.addAll(PRECACHE)),
  )
  // No skipWaiting() here: activation is the user's decision (see SKIP_WAITING below).
})

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keep = new Set([STATIC_CACHE, RUNTIME_CACHE])
    const names = await caches.keys()
    await Promise.all(names.filter(n => n.startsWith('polychem-') && !keep.has(n)).map(n => caches.delete(n)))
    await self.clients.claim()
  })())
})

self.addEventListener('message', (event) => {
  const type = event.data && event.data.type
  if (type === 'SKIP_WAITING') self.skipWaiting()
  // Sent on sign-out: belt and braces, the worker holds nothing private anyway.
  if (type === 'CLEAR_CACHES') {
    event.waitUntil(caches.keys().then(names => Promise.all(names.filter(n => n.startsWith('polychem-runtime-')).map(n => caches.delete(n)))))
  }
})

function isCacheableStatic(url) {
  // /_nuxt/builds/ holds Nuxt's own deploy-detection manifest: it must always hit the network.
  if (url.pathname.startsWith('/_nuxt/builds/')) return false
  return url.pathname.startsWith('/_nuxt/')
    || url.pathname.startsWith('/_fonts/')
    || url.pathname.startsWith('/icons/')
    || url.pathname.startsWith('/splash/')
    || url.pathname === '/manifest.webmanifest'
    || url.pathname === '/favicon.ico'
    || url.pathname === '/favicon.png'
}

async function cacheFirst(request) {
  const cache = await caches.open(RUNTIME_CACHE)
  const hit = await cache.match(request)
  if (hit) return hit
  const res = await fetch(request)
  if (res.status === 200 && res.type === 'basic') cache.put(request, res.clone())
  return res
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(RUNTIME_CACHE)
  const hit = await cache.match(request)
  const refresh = fetch(request).then((res) => {
    if (res.status === 200 && res.type === 'basic') cache.put(request, res.clone())
    return res
  }).catch(() => hit)
  return hit || refresh
}

self.addEventListener('fetch', (event) => {
  const request = event.request
  if (request.method !== 'GET') return
  if (request.headers.has('authorization') || request.headers.has('range')) return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  if (PRIVATE_PREFIXES.some(p => url.pathname.startsWith(p))) return

  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        return await fetch(request)
      }
      catch {
        const cache = await caches.open(STATIC_CACHE)
        return (await cache.match(OFFLINE_URL)) || Response.error()
      }
    })())
    return
  }

  if (!isCacheableStatic(url)) return

  const hashed = url.pathname.startsWith('/_nuxt/') || url.pathname.startsWith('/_fonts/')
  event.respondWith(hashed ? cacheFirst(request) : staleWhileRevalidate(request))
})

// ── Web Push ───────────────────────────────────────────────────────────────────────────────────
const IS_IOS = /iPhone|iPad|iPod/i.test(self.navigator.userAgent)

function safePath(url) {
  try {
    const u = new URL(url || '/notifications', self.location.origin)
    return u.origin === self.location.origin ? u.pathname + u.search + u.hash : '/notifications'
  }
  catch { return '/notifications' }
}

self.addEventListener('push', (event) => {
  let data = {}
  try { data = event.data ? event.data.json() : {} }
  catch { data = {} }
  const title = data.title || 'اعلان جدید در پلیکم'

  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    // let an open app refresh its bell immediately
    windows.forEach(c => c.postMessage({ type: 'PUSH_RECEIVED', id: data.id, unread: data.unread }))

    if (typeof data.unread === 'number' && self.navigator.setAppBadge) {
      try { data.unread > 0 ? await self.navigator.setAppBadge(data.unread) : await self.navigator.clearAppBadge() }
      catch { /* badge not supported */ }
    }

    // If the user is looking at the app, the in-app toast already tells them. iOS (and test pushes) must always
    // show a notification: WebKit revokes a subscription that receives "silent" pushes.
    const looking = windows.some(c => c.visibilityState === 'visible' && c.focused)
    if (looking && !IS_IOS && data.type !== 'TEST') return

    await self.registration.showNotification(title, {
      body: data.body || undefined,
      icon: '/icons/icon-192.png',
      badge: '/icons/icon-48.png',
      tag: data.tag || undefined, // the same tag replaces, never stacks: duplicates collapse into one
      dir: 'rtl',
      lang: 'fa',
      data: { url: safePath(data.url), id: data.id },
      timestamp: data.ts ? Date.parse(data.ts) || Date.now() : Date.now(),
    })
  })())
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const path = safePath(event.notification.data && event.notification.data.url)
  event.waitUntil((async () => {
    const windows = await self.clients.matchAll({ type: 'window', includeUncontrolled: true })
    const open = windows.find(c => 'focus' in c)
    if (open) {
      await open.focus()
      open.postMessage({ type: 'NAVIGATE', url: path })
      return
    }
    await self.clients.openWindow(path)
  })())
})

// The browser rotated the subscription: the worker has no session, so ask an open app to re-register it
// (otherwise the next start does, see sync() in usePush).
self.addEventListener('pushsubscriptionchange', (event) => {
  event.waitUntil(self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windows) => {
    windows.forEach(c => c.postMessage({ type: 'PUSH_RESYNC' }))
  }))
})
