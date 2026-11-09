// Centralized client for the Polychem Flask backend (Phase 5).
// Single base URL (repoint via NUXT_PUBLIC_API_BASE), credentials
// included so the backend's HttpOnly refresh cookie flows automatically
// (backend CORS already allows this origin with supports_credentials).
// The short-lived access token is kept in memory only (auth store),
// never persisted -- a page reload re-derives it via POST /api/auth/refresh.

export interface ApiEnvelopeError {
  success: false
  error: { code: string, message: string, details?: unknown }
}
export interface ApiEnvelopeOk<T> {
  success: true
  data: T
  meta?: { page: number, per_page: number, total: number }
}
export type ApiEnvelope<T> = ApiEnvelopeOk<T> | ApiEnvelopeError

export class ApiError extends Error {
  code: string
  status: number
  details?: unknown

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

function apiBase(): string {
  const config = useRuntimeConfig()
  return (config.public.apiBase as string) || 'http://localhost:5000/api'
}

let refreshInFlight: Promise<boolean> | null = null

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

/** Only a definite "no" from the server (401/403) ends the session. A dropped connection, a
 *  proxy hiccup or a 5xx during a reload is retried -- otherwise a momentary network blip looked
 *  exactly like "logged out". */
async function doRefresh(): Promise<boolean> {
  const authStore = useAuthStore()
  const MAX_ATTEMPTS = 3
  for (let attempt = 1; attempt <= MAX_ATTEMPTS; attempt++) {
    try {
      const res = await $fetch<ApiEnvelope<{ access_token: string, token_type: string, expires_in: number }>>(
        `${apiBase()}/auth/refresh`,
        { method: 'POST', credentials: 'include' },
      )
      if (res.success) {
        authStore.setAccessToken(res.data.access_token)
        return true
      }
      return false
    }
    catch (err: any) {
      const status = err?.response?.status ?? err?.statusCode
      const definitive = typeof status === 'number' && status >= 400 && status < 500 && status !== 408 && status !== 429
      if (definitive || attempt === MAX_ATTEMPTS) {
        authStore.setAccessToken(null)
        return false
      }
      await sleep(400 * attempt)
    }
  }
  return false
}

/** Calls POST /api/auth/refresh at most once concurrently -- several
 * requests failing with 401 at the same time share a single refresh. */
function refreshOnce(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = doRefresh().finally(() => {
      refreshInFlight = null
    })
  }
  return refreshInFlight
}

/** Public wrapper so callers (e.g. the auth store's bootstrap()) can
 * trigger/await the same de-duplicated refresh without going through
 * apiFetch's generic 401-retry wrapper (which would be redundant when
 * the caller is refresh itself). */
export async function refreshSession(): Promise<boolean> {
  return refreshOnce()
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PATCH' | 'DELETE' | 'PUT'
  body?: unknown
  query?: Record<string, string | number | boolean | undefined>
  /** Internal: set to skip the silent-refresh-and-retry on a 401. */
  _isRetry?: boolean
}

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const authStore = useAuthStore()
  const headers: Record<string, string> = {}
  if (authStore.accessToken) {
    headers.Authorization = `Bearer ${authStore.accessToken}`
  }

  try {
    const res = await $fetch<ApiEnvelope<T>>(`${apiBase()}${path}`, {
      method: options.method || 'GET',
      body: options.body as any,
      query: options.query,
      credentials: 'include',
      headers,
    })
    if (!res.success) {
      // $fetch normally throws on non-2xx, but guard the shape anyway.
      throw new ApiError(200, res.error.code, res.error.message, res.error.details)
    }
    return res.data
  }
  catch (err: any) {
    const status = err?.response?.status ?? err?.statusCode
    const body = err?.response?._data ?? err?.data

    if (status === 401 && !options._isRetry) {
      const refreshed = await refreshOnce()
      if (refreshed) {
        return apiFetch<T>(path, { ...options, _isRetry: true })
      }
    }

    if (body?.error) {
      throw new ApiError(status ?? 0, body.error.code, body.error.message, body.error.details)
    }
    throw new ApiError(status ?? 0, 'NETWORK_ERROR', err?.message || 'Request failed')
  }
}

/** Paginated GET -- returns both data and the meta envelope (page/per_page/total). */
export async function apiFetchPage<T>(
  path: string,
  query?: Record<string, string | number | boolean | undefined>,
  _isRetry = false,
): Promise<{ items: T[], total: number, page: number, perPage: number }> {
  const authStore = useAuthStore()
  const headers: Record<string, string> = {}
  if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`

  try {
    const res = await $fetch<ApiEnvelopeOk<T[]>>(`${apiBase()}${path}`, {
      method: 'GET',
      query,
      credentials: 'include',
      headers,
    })
    return {
      items: res.data,
      total: res.meta?.total ?? res.data.length,
      page: res.meta?.page ?? 1,
      perPage: res.meta?.per_page ?? res.data.length,
    }
  }
  catch (err: any) {
    const status = err?.response?.status ?? err?.statusCode
    if (status === 401 && !_isRetry) {
      const refreshed = await refreshOnce()
      if (refreshed) return apiFetchPage<T>(path, query, true)
    }
    const body = err?.response?._data ?? err?.data
    if (body?.error) throw new ApiError(status ?? 0, body.error.code, body.error.message, body.error.details)
    throw new ApiError(status ?? 0, 'NETWORK_ERROR', err?.message || 'Request failed')
  }
}
// ── paste at the END of app/services/backendApi.ts ──
/** GET a file as a Blob (same auth + silent-refresh behaviour as apiFetch). */
export async function apiFetchBlob(path: string, _isRetry = false): Promise<Blob> {
  const authStore = useAuthStore()
  const headers: Record<string, string> = {}
  if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`

  try {
    return await $fetch<Blob>(`${apiBase()}${path}`, {
      method: 'GET',
      responseType: 'blob',
      credentials: 'include',
      headers,
    })
  }
  catch (err: any) {
    const status = err?.response?.status ?? err?.statusCode
    if (status === 401 && !_isRetry) {
      const refreshed = await refreshOnce()
      if (refreshed) return apiFetchBlob(path, true)
    }
    // error bodies are JSON even though we asked for a blob
    let message = err?.message || 'Download failed'
    try {
      const blob = err?.response?._data
      if (blob instanceof Blob) message = JSON.parse(await blob.text())?.error?.message ?? message
    }
    catch { /* keep the generic message */ }
    throw new ApiError(status ?? 0, 'DOWNLOAD_FAILED', message)
  }
}