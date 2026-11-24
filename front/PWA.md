# Polychem PWA

Frontend-only (Nuxt SPA, `ssr: false`). No new npm dependency: the worker and manifest are plain files in `public/`.

| File | Purpose |
|---|---|
| `public/manifest.webmanifest` | name, RTL/fa, standalone display, icons (any + maskable), shortcuts |
| `public/sw.js` | service worker (see the header comment for what is and is not cached) |
| `public/offline.html` | shown when a navigation fails because there is no network |
| `public/icons/*`, `public/splash/*` | app icons and iOS splash images |
| `app/plugins/pwa.client.ts` | registers the worker (production only), install / update events |
| `app/composables/usePwa.ts` | shared PWA state |
| `app/components/PwaStatus.vue` | offline notice, "new version" bar, install suggestion |

## Deployment requirements

* Serve over **HTTPS** (service workers and install prompts do not work on plain HTTP except `localhost`).
* `sw.js`, `manifest.webmanifest` and `offline.html` must be served with `Cache-Control: no-cache` so updates are seen.
  `/_nuxt/*` may stay `immutable`.
* Do not cache `/api/*` at the reverse proxy either (the backend now sends `Cache-Control: no-store` on JSON answers).
* Bump `VERSION` in `sw.js` when the worker's behaviour changes.

## Update flow

A new worker installs and waits; the app shows "نسخه جدید سامانه آماده است" and reloads only after the user taps
«به‌روزرسانی» (so a half-filled form is never lost). The app also checks for a new version when it returns to the
foreground and hourly.

## Session in the installed app

The access token is memory-only; the refresh cookie is HttpOnly + SameSite=Strict (14 days) and `apiFetch` refreshes
on 401, so reopening the app signs the user in silently. Android and desktop installs share the browser's cookie jar.
**iOS keeps a separate cookie jar for a Home-Screen app**: users sign in once inside the installed app.

## Not supported / limits

* Push notifications: implemented, see `PUSH_NOTIFICATION.md` in the project root (iOS needs 16.4+ and an installed app).
* Offline use: only the offline notice; the panel needs the API, and private data is intentionally never cached.
* iOS: no install prompt (Share -> Add to Home Screen), no `beforeinstallprompt`, splash images are per device size.
* Firefox desktop cannot install PWAs.

## Install landing page (`/install`)

Mobile browsers see a one-time "install the app" page before sign-in; everyone else goes straight to sign-in.

* `middleware/01.install-gate.global.ts` runs only when navigating to `/auth/signin` (so the authentication guard and
  routes are untouched) and diverts to `/install` when `shouldShowInstallPage()` (`utils/installGate.ts`) is true:
  phone/tablet browser, not running standalone, not installed from this browser, "continue in browser" never chosen.
* **نصب اپلیکیشن**: `beforeinstallprompt` (captured by `plugins/pwa.client.ts`) -> the browser's install dialog; if the
  browser offers none (iOS Safari, Firefox, Samsung ...), short manual steps are shown. Declined -> "نصب کامل نشد ...".
* **ادامه در مرورگر**: stores `polychem:install-choice=browser` and goes to `/auth/signin`; the page never returns.
* Desktop, the installed app (`display-mode: standalone`) and later visits redirect to sign-in. `polychem:pwa-installed`
  remembers an install from this browser (a browser cannot reliably tell a normal tab that the app is installed).
