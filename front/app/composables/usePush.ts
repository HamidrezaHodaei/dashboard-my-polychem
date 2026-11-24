// Web Push for the signed-in user on THIS browser/device, plus the list of all their devices.
// The service worker (public/sw.js) receives and shows the notifications; this composable only manages
// the subscription and talks to /api/push.
import { apiFetch, ApiError } from '~/services/backendApi'

export interface PushDevice {
  id: number
  label: string | null
  platform: string | null
  created_at: string | null
  last_seen_at: string | null
  last_success_at: string | null
  last_error: string | null
  active: boolean
  is_current: boolean
}

export interface PushCategoryPref { key: string, label: string, description: string, push_enabled: boolean }
export interface PushPreferences {
  push_enabled: boolean
  show_preview: boolean
  quiet_enabled: boolean
  quiet_start: string
  quiet_end: string
  categories: PushCategoryPref[]
}

export const usePush = () => {
  const auth = useAuthStore()
  const pwa = usePwa()

  const serverEnabled = useState<boolean | null>('push:server-enabled', () => null)
  const permission = useState<NotificationPermission | 'unsupported'>('push:permission', () => 'default')
  const enabledHere = useState<boolean>('push:enabled-here', () => false)
  const devices = useState<PushDevice[]>('push:devices', () => [])
  const busy = useState<boolean>('push:busy', () => false)

  const supported = computed(() => pushSupported())
  // iOS delivers web push only to a web app that was added to the Home Screen.
  const needsInstall = computed(() => pwa.isIos.value && !pwa.isStandalone.value)
  const blocked = computed(() => permission.value === 'denied')
  const available = computed(() => supported.value && serverEnabled.value !== false && !needsInstall.value)
  /** show a "turn it on" suggestion: push is possible (or needs the install step) and not yet enabled here */
  const canOffer = computed(() => !enabledHere.value && !blocked.value && serverEnabled.value !== false
    && (supported.value || needsInstall.value))

  const flagKey = () => (auth.user ? pushFlagKey(auth.user.id) : null)
  const flagged = () => {
    const k = flagKey()
    try { return !!k && localStorage.getItem(k) === '1' }
    catch { return false }
  }
  const setFlag = (on: boolean) => {
    const k = flagKey()
    if (!k) return
    try { on ? localStorage.setItem(k, '1') : localStorage.removeItem(k) }
    catch { /* storage blocked */ }
  }

  async function loadConfig(): Promise<string | null> {
    const cfg = await apiFetch<{ enabled: boolean, public_key: string | null }>('/push/config')
    serverEnabled.value = cfg.enabled
    return cfg.public_key
  }

  async function loadDevices() {
    const sub = await currentPushSubscription()
    const data = await apiFetch<{ items: PushDevice[] }>('/push/subscriptions', { query: { endpoint: sub?.endpoint } })
    devices.value = data.items
  }

  async function register(sub: PushSubscription) {
    const json = sub.toJSON()
    await apiFetch('/push/subscriptions', {
      method: 'POST',
      body: { endpoint: sub.endpoint, p256dh: json.keys?.p256dh, auth: json.keys?.auth },
    })
  }

  /** Cheap state refresh for pages that show push status. */
  async function refreshState() {
    if (!import.meta.client) return
    permission.value = supported.value ? Notification.permission : 'unsupported'
    try {
      await loadConfig()
      const sub = await currentPushSubscription()
      enabledHere.value = !!sub && flagged() && Notification.permission === 'granted'
      if (supported.value && serverEnabled.value) await loadDevices()
    }
    catch { /* offline / signed out: keep the last known state */ }
  }

  /** Called when the app opens signed in: keep this device's registration fresh, or restore it if the browser
   *  dropped it. Only for a browser the CURRENT user switched on -- never binds a leftover subscription. */
  async function sync() {
    if (!supported.value || !auth.user) return
    permission.value = Notification.permission
    if (!flagged() || Notification.permission !== 'granted') {
      enabledHere.value = false
      return
    }
    try {
      const key = await loadConfig()
      if (!key || !serverEnabled.value) return
      const reg = await navigator.serviceWorker.ready
      let sub = await reg.pushManager.getSubscription()
      // a rotated VAPID key makes the old subscription useless: start over with the new one
      const current = sub?.options?.applicationServerKey
      const wanted = urlBase64ToUint8Array(key)
      if (sub && current && !sameBytes(new Uint8Array(current), wanted)) {
        await sub.unsubscribe()
        sub = null
      }
      sub ??= await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: wanted as BufferSource })
      await register(sub)
      enabledHere.value = true
    }
    catch { /* try again on the next start */ }
  }

  /** Must run from a user gesture (a click): the permission prompt is only shown then. */
  async function enable(): Promise<{ ok: boolean, message?: string }> {
    if (!supported.value) return { ok: false, message: 'این مرورگر از اعلان فوری پشتیبانی نمی‌کند.' }
    if (needsInstall.value) return { ok: false, message: 'ابتدا سامانه را از منوی اشتراک‌گذاری به صفحه اصلی اضافه کنید.' }
    busy.value = true
    try {
      const key = await loadConfig()
      if (!key || !serverEnabled.value) return { ok: false, message: 'اعلان فوری هنوز روی سرور فعال نشده است.' }
      const result = await Notification.requestPermission()
      permission.value = result
      if (result !== 'granted') {
        return { ok: false, message: result === 'denied' ? 'مرورگر اجازهٔ اعلان را مسدود کرده است؛ از تنظیمات سایت آن را فعال کنید.' : 'اجازهٔ اعلان داده نشد.' }
      }
      const reg = await navigator.serviceWorker.ready
      const sub = (await reg.pushManager.getSubscription())
        ?? await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(key) as BufferSource })
      await register(sub)
      setFlag(true)
      enabledHere.value = true
      await loadDevices()
      return { ok: true }
    }
    catch (e) {
      return { ok: false, message: e instanceof ApiError ? e.message : 'فعال‌سازی اعلان انجام نشد. دوباره تلاش کنید.' }
    }
    finally {
      busy.value = false
    }
  }

  async function disable() {
    busy.value = true
    try {
      await detachCurrentDevice(auth.user?.id)
      enabledHere.value = false
      await loadDevices().catch(() => {})
    }
    finally {
      busy.value = false
    }
  }

  async function removeDevice(id: number) {
    const target = devices.value.find(d => d.id === id)
    await apiFetch(`/push/subscriptions/${id}`, { method: 'DELETE' })
    if (target?.is_current) {
      const sub = await currentPushSubscription()
      await sub?.unsubscribe().catch(() => {})
      setFlag(false)
      enabledHere.value = false
    }
    await loadDevices()
  }

  async function testDevice(id: number): Promise<{ ok: boolean, error?: string | null }> {
    const r = await apiFetch<{ ok: boolean, error: string | null }>(`/push/subscriptions/${id}/test`, { method: 'POST' })
    await loadDevices().catch(() => {})
    return { ok: r.ok, error: r.error }
  }

  return {
    supported, needsInstall, blocked, available, canOffer, serverEnabled, permission, enabledHere, devices, busy,
    refreshState, sync, enable, disable, removeDevice, testDevice, loadDevices,
  }
}

function sameBytes(a: Uint8Array, b: Uint8Array): boolean {
  return a.length === b.length && a.every((v, i) => v === b[i])
}
