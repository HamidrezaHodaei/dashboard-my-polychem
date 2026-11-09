// Wraps the real Pinia auth store (Phase 5) behind the same `useAuth()`
// shape the rest of the app already calls (login/logout/isLoggedIn/user),
// so existing consumers (HeaderUserMenu, LayoutSidebarFooter, signin.vue,
// the global route middleware) don't need to change how they call it --
// only what backs it changed, from nuxt-auth-utils' mock session to the
// real Flask backend.
export const useAuth = () => {
  const authStore = useAuthStore()

  const isLoggedIn = computed(() => authStore.isLoggedIn)
  const user = computed(() => authStore.user)

  const login = async (credentials: { email: string, password: string }) => {
    // Backend accepts email OR username as `identifier` (SECURITY.md:
    // no enumeration between the two) -- the sign-in form only collects
    // an email-shaped value today, so it's passed straight through.
    await authStore.login(credentials.email, credentials.password)
  }

  const logout = async () => {
    await authStore.logout()
  }

  return {
    isLoggedIn,
    user,
    login,
    logout,
  }
}
