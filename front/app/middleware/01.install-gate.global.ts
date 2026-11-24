// First-visit "install the app" page for mobile browsers.
//
// It does not touch the authentication guard: when that guard sends a signed-out visitor to the sign-in page,
// this runs first for that navigation and, only if /install is appropriate, diverts to it once. "Continue in
// browser" only skips it for the current browser session (so the click reaches sign-in); on the next visit it
// shows again until the app is installed. The installed app and desktop browsers never see it. Named 01.* so it runs before auth.global.
export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return
  if (to.path !== '/auth/signin') return
  if (shouldShowInstallPage()) return navigateTo('/install', { replace: true })
})
