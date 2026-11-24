// Browser-side Web Push helpers that need no Nuxt composable context (also used by the auth store at sign-out).
import { apiFetch } from '~/services/backendApi'

export function urlBase64ToUint8Array(value: string): Uint8Array {
  const padded = value + '='.repeat((4 - (value.length % 4)) % 4)
  const raw = atob(padded.replace(/-/g, '+').replace(/_/g, '/'))
  const out = new Uint8Array(new ArrayBuffer(raw.length))
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

export const pushSupported = () => import.meta.client
  && 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window

/** localStorage flag: "this browser was switched on for push by user N". A subscription that exists without the flag
 *  of the signed-in user is never auto-bound to them (it may belong to the previous user of a shared computer). */
export const pushFlagKey = (userId: number | string) => `polychem:push:${userId}`

export async function currentPushSubscription(): Promise<PushSubscription | null> {
  if (!pushSupported()) return null
  const reg = await navigator.serviceWorker.getRegistration('/')
  return (await reg?.pushManager.getSubscription()) ?? null
}

/** Sign-out: forget this device on the server (for the signed-in user only) and drop the browser subscription,
 *  so the next person on this browser gets a fresh endpoint of their own. Best effort, never throws. */
export async function detachCurrentDevice(userId?: number | null): Promise<void> {
  try {
    const sub = await currentPushSubscription()
    if (sub) {
      await apiFetch('/push/subscriptions/detach', { method: 'POST', body: { endpoint: sub.endpoint } }).catch(() => {})
      await sub.unsubscribe().catch(() => {})
    }
    if (userId) localStorage.removeItem(pushFlagKey(userId))
  }
  catch { /* nothing to detach */ }
}
