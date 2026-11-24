// Registers the service worker (production only: in dev it would cache half-built modules) and wires the
// install / update events into usePwa(). The worker itself lives in public/sw.js.
export default defineNuxtPlugin(() => {
  const pwa = usePwa()
  pwa.loadDismissed()

  window.addEventListener('beforeinstallprompt', (e) => {
    e.preventDefault() // we show our own, quieter suggestion instead of the browser mini-bar
    pwa.installEvent.value = e as never
  })
  if (isStandaloneMode()) rememberInstalled()
  window.addEventListener('appinstalled', () => {
    rememberInstalled()
    pwa.installed.value = true
    pwa.installEvent.value = null
  })

  if (import.meta.dev || !('serviceWorker' in navigator)) return

  // Reload exactly once when a new worker takes control (after the user accepted the update).
  let reloading = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (reloading) return
    reloading = true
    window.location.reload()
  })

  const watch = (reg: ServiceWorkerRegistration) => {
    const announce = (worker: ServiceWorker | null) => {
      // `controller` is null on the very first install: that is not an update.
      if (worker && navigator.serviceWorker.controller) pwa.updateWorker.value = worker
    }
    if (reg.waiting) announce(reg.waiting)
    reg.addEventListener('updatefound', () => {
      const incoming = reg.installing
      incoming?.addEventListener('statechange', () => {
        if (incoming.state === 'installed') announce(incoming)
      })
    })
    // A long-lived installed app never "loads" again, so look for a new version when it comes back to the
    // foreground and every hour while it stays open.
    const check = () => { reg.update().catch(() => {}) }
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') check()
    })
    window.setInterval(check, 60 * 60 * 1000)
  }

  // In a client-only (ssr: false) app this plugin can run AFTER the window "load" event already fired, so waiting
  // for "load" would never register the worker. Register right away in that case.
  const registerWorker = () => {
    navigator.serviceWorker
      .register('/sw.js', { scope: '/', updateViaCache: 'none' })
      .then(watch)
      .catch((e) => { console.warn('[pwa] service worker registration failed:', e) })
  }
  if (document.readyState === 'complete') registerWorker()
  else window.addEventListener('load', registerWorker, { once: true })
})
