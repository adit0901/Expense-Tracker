/**
 * API client: attaches the in-memory access token, refreshes it once (single flight) on 401
 * using the httpOnly refresh cookie, and maps the error envelope to ApiError.
 */
import type { ErrorDetail } from './types'

export const API_PREFIX = '/api/v1'

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: ErrorDetail[]
  readonly requestId: string | null

  constructor(status: number, code: string, message: string, details: ErrorDetail[] = [],
              requestId: string | null = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }

  /** Field-level messages keyed by field name (from 422 details). */
  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {}
    for (const d of this.details) {
      if (typeof d.field === 'string' && d.field && !(d.field in out)) {
        out[d.field] = typeof d.message === 'string' && d.message.length > 20 ? d.message : this.message
      }
    }
    return out
  }
}

// ---- token store (memory only; never localStorage) ----------------------------------------
let accessToken: string | null = null
export const tokenStore = {
  get: () => accessToken,
  set: (t: string | null) => {
    accessToken = t
  },
}

type AuthFailureHandler = () => void
let onAuthFailure: AuthFailureHandler = () => {}
export function setAuthFailureHandler(handler: AuthFailureHandler): void {
  onAuthFailure = handler
}

type TokenListener = (token: { access_token: string; user: unknown } | null) => void
let tokenListener: TokenListener = () => {}
export function setTokenListener(fn: TokenListener): void {
  tokenListener = fn
}

let refreshInFlight: Promise<boolean> | null = null

function absolute(path: string): string {
  const base = typeof window !== 'undefined' ? window.location.origin : 'http://localhost'
  return new URL(path.startsWith('/api') ? path : `${API_PREFIX}${path}`, base).toString()
}

/** Single-flight refresh: concurrent 401s share one refresh request. */
export function refreshAccessToken(): Promise<boolean> {
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(absolute('/auth/refresh'), { method: 'POST', credentials: 'include' })
        if (!res.ok) {
          tokenStore.set(null)
          tokenListener(null)
          return false
        }
        const body = (await res.json()) as { data: { access_token: string; user: unknown } }
        tokenStore.set(body.data.access_token)
        tokenListener(body.data)
        return true
      } catch {
        tokenStore.set(null)
        return false
      } finally {
        // Callers already hold this promise; later 401s start a fresh refresh.
        refreshInFlight = null
      }
    })()
  }
  return refreshInFlight
}

export type Query = Record<string, string | number | boolean | null | undefined | Array<string | number>>

export function buildQuery(query?: Query): string {
  if (!query) return ''
  const params = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((item) => params.append(k, String(item)))
    else params.append(k, String(v))
  }
  const s = params.toString()
  return s ? `?${s}` : ''
}

export interface RequestOptions {
  method?: string
  body?: unknown
  query?: Query
  headers?: Record<string, string>
  signal?: AbortSignal
  /** Do not attach a token or attempt refresh (public auth endpoints). */
  anonymous?: boolean
  /** Return the raw Response (downloads). */
  raw?: boolean
}

async function toError(res: Response): Promise<ApiError> {
  try {
    const body = (await res.json()) as {
      error?: { code: string; message: string; details?: ErrorDetail[]; request_id?: string }
    }
    if (body.error) {
      return new ApiError(res.status, body.error.code, body.error.message, body.error.details ?? [],
        body.error.request_id ?? null)
    }
  } catch {
    /* non-JSON body */
  }
  return new ApiError(res.status, 'http_error', `Request failed (${res.status})`)
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = { Accept: 'application/json', ...opts.headers }
  let body: BodyInit | undefined
  if (opts.body instanceof FormData) body = opts.body
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  const token = tokenStore.get()
  if (token && !opts.anonymous) headers.Authorization = `Bearer ${token}`
  return fetch(absolute(path) + buildQuery(opts.query), {
    method: opts.method ?? 'GET',
    headers,
    body,
    credentials: 'include',
    signal: opts.signal,
  })
}

export async function request<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res = await send(path, opts)
  if (res.status === 401 && !opts.anonymous) {
    const refreshed = await refreshAccessToken()
    if (refreshed) res = await send(path, opts)
    else {
      onAuthFailure()
      throw await toError(res)
    }
  }
  if (!res.ok) throw await toError(res)
  if (opts.raw) return res as unknown as T
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}

/** Unwrap `{data}` from the success envelope. */
export async function getData<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const body = await request<{ data: T }>(path, opts)
  return body.data
}

export const api = {
  get: <T>(path: string, query?: Query) => getData<T>(path, { query }),
  page: <T>(path: string, query?: Query) => request<T>(path, { query }),
  post: <T>(path: string, body?: unknown, extra: Partial<RequestOptions> = {}) =>
    getData<T>(path, { method: 'POST', body, ...extra }),
  put: <T>(path: string, body?: unknown) => getData<T>(path, { method: 'PUT', body }),
  patch: <T>(path: string, body?: unknown) => getData<T>(path, { method: 'PATCH', body }),
  del: (path: string, query?: Query, body?: unknown) =>
    request<unknown>(path, { method: 'DELETE', query, body }),
}

/** Download a file (CSV, receipt) via an authenticated request. */
export async function download(path: string, query?: Query, fallbackName = 'download'): Promise<void> {
  const res = await request<Response>(path, { query, raw: true })
  const blob = await res.blob()
  const disposition = res.headers.get('Content-Disposition') ?? ''
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(disposition)
  const name = match?.[1] ? decodeURIComponent(match[1]) : fallbackName
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
