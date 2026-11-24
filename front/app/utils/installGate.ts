// Decides whether the "install the app" landing page (/install) may be shown. Pure client-side helpers.
//
// Shown on every visit when ALL hold: a phone/tablet browser, not already running as the installed app, and the
// app was not installed from this browser before. Anything else goes straight to the sign-in page.
//
// "Continue in browser" is remembered for the current browser session only (sessionStorage), so that the click
// reaches the sign-in page instead of bouncing back to /install. On the next visit the page shows again.

const CHOICE_KEY = 'polychem:install-choice' // 'browser' for this session once the visitor picked "continue in browser"
const INSTALLED_KEY = 'polychem:pwa-installed' // '1' once the app was installed (or opened) from this browser

const read = (k: string) => {
  try { return localStorage.getItem(k) }
  catch { return null }
}
const write = (k: string, v: string) => {
  try { localStorage.setItem(k, v) }
  catch { /* storage blocked: the page may show again, which is harmless */ }
}
// Session-scoped (cleared when the tab/browser session ends): the "continue in browser" choice must not persist.
const readSession = (k: string) => {
  try { return sessionStorage.getItem(k) }
  catch { return null }
}
const writeSession = (k: string, v: string) => {
  try { sessionStorage.setItem(k, v) }
  catch { /* storage blocked: the visitor may be sent back to /install, which is harmless */ }
}

export function isMobileDevice(): boolean {
  if (!import.meta.client) return false
  const ua = navigator.userAgent
  const phoneOrTablet = /Android|iPhone|iPad|iPod|Mobile|Windows Phone/i.test(ua)
  const ipadOs = ua.includes('Macintosh') && navigator.maxTouchPoints > 1 // iPadOS reports itself as a Mac
  return phoneOrTablet || ipadOs
}

export function isStandaloneMode(): boolean {
  if (!import.meta.client) return false
  return window.matchMedia('(display-mode: standalone)').matches
    || window.matchMedia('(display-mode: window-controls-overlay)').matches
    || (navigator as Navigator & { standalone?: boolean }).standalone === true
}

export const chosenBrowser = () => readSession(CHOICE_KEY) === 'browser'
export const rememberBrowserChoice = () => writeSession(CHOICE_KEY, 'browser')
export const wasInstalled = () => read(INSTALLED_KEY) === '1'
export const rememberInstalled = () => write(INSTALLED_KEY, '1')

export function shouldShowInstallPage(): boolean {
  if (!import.meta.client) return false
  if (isStandaloneMode()) { rememberInstalled(); return false } // opened as the installed app
  return isMobileDevice() && !wasInstalled() && !chosenBrowser()
}
