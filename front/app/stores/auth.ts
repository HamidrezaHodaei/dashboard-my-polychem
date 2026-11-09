import { defineStore } from 'pinia'
import { ApiError, apiFetch, refreshSession } from '~/services/backendApi'

export interface BackendUser {
  id: number
  full_name: string
  email: string
  username: string
  organization_id: number | null
  department_id: number | null
  is_active: boolean
  last_login_at: string | null
  created_at: string
  updated_at: string
  /** the roles the user holds (read-only for the user; only an admin changes them) */
  roles?: { name: string, display_name: string | null }[]
  /** profile photo as a small data URL, or null */
  avatar?: string | null
}

export interface EffectivePermission {
  key: string
  scopes: { scope_type: string, scope_id: number | null, source: string }[]
}

export interface NavigationItem {
  key: string
  label: string
  path: string
  permission: string
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as BackendUser | null,
    accessToken: null as string | null,
    permissions: [] as EffectivePermission[],
    navigation: [] as NavigationItem[],
    /** Set once bootstrap() (silent refresh + /api/me) has resolved,
     * successfully or not -- lets the route guard wait instead of
     * bouncing to /auth/signin on a hard page reload before the
     * refresh cookie has had a chance to prove the session. */
    bootstrapped: false,
  }),
  getters: {
    isLoggedIn: state => !!state.user,
    permissionKeys: state => new Set(state.permissions.map(p => p.key)),
    navigationKeys: state => new Set(state.navigation.map(n => n.key)),
    isAdmin: state => !!state.user?.roles?.some(r => r.name === 'admin'),
  },
  actions: {
    setAccessToken(token: string | null) {
      this.accessToken = token
    },

    async login(identifier: string, password: string) {
      const data = await apiFetch<{ access_token: string, token_type: string, expires_in: number }>(
        '/auth/login',
        { method: 'POST', body: { identifier, password } },
      )
      this.accessToken = data.access_token
      useTaskWorkspaceStore().reset()
      useNotificationsStore().reset()
      await this.loadSession()
    },

    async logout() {
      try {
        await apiFetch('/auth/logout', { method: 'POST' })
      }
      catch {
        // Logout must always clear local state even if the network call
        // fails (backend's own /auth/logout is itself idempotent/always-200).
      }
      this.user = null
      this.accessToken = null
      this.permissions = []
      this.navigation = []
      useTaskWorkspaceStore().reset()
      useNotificationsStore().reset()
    },

    /** Loads /api/me, /api/me/permissions, /api/me/navigation once an
     * access token is available (after login, or after a successful
     * silent refresh in bootstrap()). */
    async loadSession() {
      const [me, permissions, navigation] = await Promise.all([
        apiFetch<BackendUser>('/me'),
        apiFetch<{ permissions: EffectivePermission[] }>('/me/permissions'),
        apiFetch<{ navigation: NavigationItem[] }>('/me/navigation'),
      ])
      // Another account signing in on the same browser tab (token expiry -> sign-in as someone
      // else, no explicit logout) must never see the previous user's cached projects / tasks.
      if (this.user && this.user.id !== me.id) {
        useTaskWorkspaceStore().reset()
        useNotificationsStore().reset()
      }
      this.user = me
      this.permissions = permissions.permissions
      this.navigation = navigation.navigation
    },

    /** Called once on app startup (client-side): tries to silently turn
     * the HttpOnly refresh cookie (if any, from a previous session) into
     * a fresh access token + session, without forcing a re-login on
     * every page reload. Never throws. */
    async bootstrap() {
      if (this.bootstrapped) return
      try {
        const refreshed = await refreshSession()
        if (refreshed) {
          await this.loadSession()
        }
      }
      catch {
        this.user = null
        this.accessToken = null
      }
      finally {
        this.bootstrapped = true
      }
    },

    /** The user's OWN photo -- the only part of the profile a user edits (name / e-mail / username / roles are admin-only). */
    async setAvatar(image: string | null) {
      this.user = image
        ? await apiFetch<BackendUser>('/me/avatar', { method: 'PUT', body: { image } })
        : await apiFetch<BackendUser>('/me/avatar', { method: 'DELETE' })
    },

    /** A user changes THEIR OWN password; other devices are signed out by the server. */
    async changePassword(current_password: string, new_password: string) {
      await apiFetch('/auth/change-password', { method: 'POST', body: { current_password, new_password } })
    },

    hasPermission(key: string): boolean {
      return this.permissionKeys.has(key)
    },
  },
})

export { ApiError }
