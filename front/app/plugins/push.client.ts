// Keeps this device's push registration in step with the signed-in user, and reacts to messages from the
// service worker (a push arrived while the app is open / a notification was tapped).
export default defineNuxtPlugin(() => {
  const auth = useAuthStore()
  const push = usePush()

  watch(() => auth.isLoggedIn, (loggedIn) => {
    if (loggedIn) push.sync()
  }, { immediate: true })

  if (!('serviceWorker' in navigator)) return
  navigator.serviceWorker.addEventListener('message', (event) => {
    const msg = event.data
    if (!msg || typeof msg !== 'object') return
    if (msg.type === 'PUSH_RECEIVED') {
      // refresh the bell right away instead of waiting for the next 20 s poll
      if (auth.isLoggedIn) useNotificationsStore().fetchNow()
    }
    else if (msg.type === 'NAVIGATE' && typeof msg.url === 'string' && msg.url.startsWith('/') && !msg.url.startsWith('//')) {
      navigateTo(msg.url)
    }
    else if (msg.type === 'PUSH_RESYNC' && auth.isLoggedIn) {
      push.sync() // the browser rotated the subscription
    }
  })
})
