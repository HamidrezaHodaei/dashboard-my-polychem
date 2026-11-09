import { defineStore } from 'pinia'
import { apiFetch } from '~/services/backendApi'

export interface AppNotification {
  id: number
  type: string
  title: string
  body: string | null
  link: string | null
  task_id: number | null
  is_read: boolean
  created_at: string
}

const POLL_MS = 20_000
const PREF_KEY = 'app:notification-prefs'

/**
 * The header bell: polls the server, keeps the unread count, and -- when something NEW
 * arrives while the app is open -- plays a short sound (and, if the user allowed it, shows a
 * system notification). The first fetch after sign-in only loads what already exists: old
 * unread items do not beep.
 */
export const useNotificationsStore = defineStore('notifications', () => {
  const items = ref<AppNotification[]>([])
  const unread = ref(0)
  const sound = ref(true)
  const desktop = ref(false)
  let lastSeenId = 0
  let primed = false
  let timer: ReturnType<typeof setInterval> | null = null
  let audio: AudioContext | null = null
  let prefsLoaded = false

  function loadPrefs() {
    if (prefsLoaded || !import.meta.client) return
    prefsLoaded = true
    try {
      const saved = JSON.parse(localStorage.getItem(PREF_KEY) || '{}')
      if (typeof saved.sound === 'boolean') sound.value = saved.sound
      if (typeof saved.desktop === 'boolean') desktop.value = saved.desktop
    }
    catch { /* defaults */ }
  }
  function savePrefs() {
    if (import.meta.client) localStorage.setItem(PREF_KEY, JSON.stringify({ sound: sound.value, desktop: desktop.value }))
  }
  function setSound(on: boolean) {
    sound.value = on
    savePrefs()
  }
  async function setDesktop(on: boolean): Promise<boolean> {
    if (on && 'Notification' in window && Notification.permission !== 'granted') {
      const result = await Notification.requestPermission()
      if (result !== 'granted') {
        desktop.value = false
        savePrefs()
        return false
      }
    }
    desktop.value = on
    savePrefs()
    return true
  }

  /** Two soft tones generated with the Web Audio API (no sound file to ship). Browsers allow
   *  audio only after the user has interacted with the page once; until then it is skipped. */
  async function playSound() {
    if (!import.meta.client) return
    try {
      audio ??= new (window.AudioContext || (window as any).webkitAudioContext)()
      if (audio.state === 'suspended') await audio.resume()
      if (audio.state !== 'running') return
      const now = audio.currentTime
      for (const [freq, offset, length] of [[880, 0, 0.16], [1318.5, 0.17, 0.26]] as const) {
        const osc = audio.createOscillator()
        const gain = audio.createGain()
        osc.type = 'sine'
        osc.frequency.value = freq
        gain.gain.setValueAtTime(0.0001, now + offset)
        gain.gain.exponentialRampToValueAtTime(0.25, now + offset + 0.02)
        gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + length)
        osc.connect(gain).connect(audio.destination)
        osc.start(now + offset)
        osc.stop(now + offset + length + 0.02)
      }
    }
    catch { /* no audio available: silently skip */ }
  }
  /** unlock audio on the first click/keypress so later alerts may play */
  function unlockAudio() {
    if (!import.meta.client) return
    const unlock = () => {
      audio ??= new (window.AudioContext || (window as any).webkitAudioContext)()
      audio.resume().catch(() => {})
      window.removeEventListener('pointerdown', unlock)
      window.removeEventListener('keydown', unlock)
    }
    window.addEventListener('pointerdown', unlock, { once: true })
    window.addEventListener('keydown', unlock, { once: true })
  }

  async function fetchNow() {
    try {
      const data = await apiFetch<{ items: AppNotification[], unread_count: number }>('/notifications', { query: { limit: 30 } })
      const fresh = primed ? data.items.filter(n => !n.is_read && n.id > lastSeenId) : []
      items.value = data.items
      unread.value = data.unread_count
      lastSeenId = Math.max(lastSeenId, ...data.items.map(n => n.id), 0)
      primed = true
      if (fresh.length) {
        if (sound.value) playSound()
        if (desktop.value && 'Notification' in window && Notification.permission === 'granted' && document.hidden) {
          const first = fresh[0]!
          new Notification(first.title, { body: first.body ?? undefined, lang: 'fa', dir: 'rtl' })
        }
        useNotify().info(fresh[0]!.title, fresh.length > 1 ? `و ${fresh.length - 1} اعلان جدید دیگر` : fresh[0]!.body ?? undefined)
      }
    }
    catch { /* offline / session expired: keep what we have, try again next tick */ }
  }

  function start() {
    if (timer || !import.meta.client) return
    loadPrefs()
    unlockAudio()
    fetchNow()
    timer = setInterval(() => { if (!document.hidden) fetchNow() }, POLL_MS)
    document.addEventListener('visibilitychange', onVisible)
  }
  const onVisible = () => { if (!document.hidden) fetchNow() }
  function stop() {
    if (timer) clearInterval(timer)
    timer = null
    if (import.meta.client) document.removeEventListener('visibilitychange', onVisible)
  }
  function reset() {
    stop()
    items.value = []
    unread.value = 0
    lastSeenId = 0
    primed = false
  }

  async function markRead(ids: number[]) {
    if (!ids.length) return
    await apiFetch('/notifications/read', { method: 'POST', body: { ids } })
    const newlyRead = items.value.filter(n => ids.includes(n.id) && !n.is_read).length
    items.value = items.value.map(n => (ids.includes(n.id) ? { ...n, is_read: true } : n))
    unread.value = Math.max(0, unread.value - newlyRead)
  }

  /** One page of the full history for the "all notifications" screen (does not touch the bell list). */
  async function fetchPage(opts: { beforeId?: number | null, unreadOnly?: boolean, limit?: number } = {}) {
    const data = await apiFetch<{
      items: AppNotification[], unread_count: number, has_more: boolean, next_before_id: number | null
    }>('/notifications', {
      query: { limit: opts.limit ?? 30, unread: opts.unreadOnly ? 1 : undefined, before_id: opts.beforeId ?? undefined },
    })
    unread.value = data.unread_count
    return data
  }
  async function markAllRead() {
    await apiFetch('/notifications/read', { method: 'POST', body: { all: true } })
    items.value = items.value.map(n => ({ ...n, is_read: true }))
    unread.value = 0
  }

  return { items, unread, sound, desktop, loadPrefs, setSound, setDesktop, playSound, start, stop, reset, fetchNow, fetchPage, markRead, markAllRead }
})
