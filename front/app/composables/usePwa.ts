// Installed-app (PWA) state, shared by the plugin that registers the service worker and by <PwaStatus>.
// Everything here is client-only state; nothing is persisted except the "not now" timestamp for the
// install suggestion.

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>
}

const DISMISS_KEY = 'polychem:pwa-install-dismissed'
const DISMISS_DAYS = 14

export const usePwa = () => {
  const installEvent = useState<BeforeInstallPromptEvent | null>('pwa:install-event', () => null)
  const updateWorker = useState<ServiceWorker | null>('pwa:update-worker', () => null)
  const installed = useState<boolean>('pwa:installed', () => false)
  const dismissedAt = useState<number>('pwa:install-dismissed-at', () => 0)

  const online = useOnline()

  const isStandalone = computed(() => {
    if (!import.meta.client) return false
    return window.matchMedia('(display-mode: standalone)').matches
      || window.matchMedia('(display-mode: window-controls-overlay)').matches
      || (navigator as Navigator & { standalone?: boolean }).standalone === true
  })

  // iOS Safari has no install prompt: the only way is Share -> Add to Home Screen.
  const isIos = computed(() => {
    if (!import.meta.client) return false
    const ua = navigator.userAgent
    return /iphone|ipad|ipod/i.test(ua) || (ua.includes('Mac') && navigator.maxTouchPoints > 1)
  })

  const recentlyDismissed = computed(() => dismissedAt.value > 0 && Date.now() - dismissedAt.value < DISMISS_DAYS * 86_400_000)

  const canInstall = computed(() => !!installEvent.value && !installed.value && !isStandalone.value && !recentlyDismissed.value)
  const showIosHint = computed(() => isIos.value && !isStandalone.value && !installed.value && !recentlyDismissed.value)
  const updateReady = computed(() => !!updateWorker.value)

  function loadDismissed() {
    try { dismissedAt.value = Number(localStorage.getItem(DISMISS_KEY)) || 0 }
    catch { /* storage blocked: just show the suggestion */ }
  }

  function dismissInstall() {
    dismissedAt.value = Date.now()
    try { localStorage.setItem(DISMISS_KEY, String(dismissedAt.value)) }
    catch { /* ignore */ }
  }

  async function install(): Promise<'accepted' | 'dismissed' | null> {
    const ev = installEvent.value
    if (!ev) return null
    await ev.prompt()
    const { outcome } = await ev.userChoice
    installEvent.value = null // the browser allows one prompt per event
    if (outcome === 'dismissed') dismissInstall()
    return outcome
  }

  /** The user accepted the update: tell the waiting worker to take over; the plugin reloads on controllerchange. */
  function applyUpdate() {
    updateWorker.value?.postMessage({ type: 'SKIP_WAITING' })
  }

  /** Sign-out: drop runtime caches (they hold no private data, this is defence in depth). */
  function clearCaches() {
    if (!import.meta.client) return
    navigator.serviceWorker?.controller?.postMessage({ type: 'CLEAR_CACHES' })
  }

  return {
    online,
    installed,
    isStandalone,
    isIos,
    canInstall,
    showIosHint,
    updateReady,
    installEvent,
    updateWorker,
    loadDismissed,
    dismissInstall,
    install,
    applyUpdate,
    clearCaches,
  }
}
