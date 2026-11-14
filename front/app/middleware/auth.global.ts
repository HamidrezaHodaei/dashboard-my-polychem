// Route guard for Phase 5: real authentication (backend JWT + refresh
// cookie via the auth store) plus a permission-gate for the sections
// that have a matching real backend permission (GET /api/me/navigation).
// Sections with no backend module yet (finance/inventory/crm/mail/...,
// Phase 6+) are left authentication-only -- there is no real permission
// to gate them by yet, and inventing one would violate this task's own
// "do not invent frontend contracts unrelated to these endpoints" rule.
const ROUTE_NAVIGATION_KEYS: Record<string, string | string[]> = {
  '/access-management/users': 'users',
  '/access-management/roles': 'roles',
  '/access-management/organizations': 'organizations',
  '/access-management/teams': 'teams',
  '/access-management/permissions': 'permissions',
  '/tasks/analytics': 'task_analytics',
  // CRM: every screen is gated by the same navigation keys the backend derives from crm.* permissions.
  '/crm/customers': 'customers',
  '/crm/sales': 'crm_sales',
  '/crm/dashboard': 'crm_dashboard',
  '/crm/request-samples': 'request_samples',
  '/crm/settings': 'crm_settings',
  '/tasks': 'tasks',
  // Logistics database: a user needs access to at least one of the two applicant types.
  '/procurement/logistics': ['logistics_companies', 'logistics_drivers'],
}

// Sections with no backend permission to grant (placeholder modules) are admin-only -- the sidebar hides
// them for everybody else, so typing the URL must not open them either.
const ADMIN_ONLY_PREFIXES = ['/finance', '/inventory', '/customer-panel', '/website']

function requiredNavigationKeyFor(path: string): string | string[] | null {
  // Longest-prefix match so `/tasks/analytics` doesn't fall through to
  // the generic `/tasks` entry.
  const candidates = Object.keys(ROUTE_NAVIGATION_KEYS)
    .filter(prefix => path === prefix || path.startsWith(`${prefix}/`))
    .sort((a, b) => b.length - a.length)
  return candidates.length ? ROUTE_NAVIGATION_KEYS[candidates[0]]! : null
}

export default defineNuxtRouteMiddleware(async (to) => {
  const authStore = useAuthStore()

  // Public/guest-only routes don't need a session at all.
  if (to.meta.public) return

  // Rehydrate the session from the backend's HttpOnly refresh cookie on
  // first navigation (e.g. a hard page reload) before deciding anything.
  if (import.meta.client && !authStore.bootstrapped) {
    try {
      await authStore.bootstrap()
    }
    catch {
      authStore.bootstrapped = true
    }
  }

  if (to.meta.guest && authStore.isLoggedIn) {
    return navigateTo('/')
  }

  if (!to.meta.guest && !authStore.isLoggedIn) {
    return navigateTo('/auth/signin')
  }

  if (!to.meta.guest && !authStore.isAdmin
    && ADMIN_ONLY_PREFIXES.some(p => to.path === p || to.path.startsWith(`${p}/`))) {
    return navigateTo('/403')
  }

  const requiredKey = requiredNavigationKeyFor(to.path)
  if (requiredKey) {
    const keys = Array.isArray(requiredKey) ? requiredKey : [requiredKey]
    if (!keys.some(k => authStore.navigationKeys.has(k))) return navigateTo('/403')
  }
})
