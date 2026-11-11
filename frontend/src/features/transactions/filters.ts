import type { Query } from '@/services/api/client'

/** Filters as they appear in the page URL (drill-down links use the same names). */
export interface TxnFilters {
  date_from?: string
  date_to?: string
  type?: string[]
  account_id?: string
  category_id?: string
  payment_method?: string
  amount_min?: string
  amount_max?: string
  tag?: string
  q?: string
  import_batch_id?: string
  sort?: string
  page?: number
}

const SCALARS = ['date_from', 'date_to', 'account_id', 'category_id', 'payment_method', 'amount_min',
  'amount_max', 'tag', 'q', 'import_batch_id', 'sort'] as const

export function filtersFromSearch(params: URLSearchParams): TxnFilters {
  const f: TxnFilters = {}
  for (const k of SCALARS) {
    const v = params.get(k)
    if (v) f[k] = v
  }
  const types = params.getAll('type').filter(Boolean)
  if (types.length) f.type = types
  const page = Number(params.get('page'))
  if (Number.isInteger(page) && page > 1) f.page = page
  return f
}

export function filtersToSearch(f: TxnFilters): URLSearchParams {
  const p = new URLSearchParams()
  for (const k of SCALARS) {
    const v = f[k]
    if (v) p.set(k, v)
  }
  for (const t of f.type ?? []) p.append('type', t)
  if (f.page && f.page > 1) p.set('page', String(f.page))
  return p
}

/** Map page filters to the API query (1:1 names; pagination added). */
export function filtersToApiQuery(f: TxnFilters, pageSize = 25): Query {
  const { page, ...rest } = f
  return { ...rest, type: rest.type, page: page ?? 1, page_size: pageSize }
}

/** Export uses the same filters without pagination. */
export function filtersToExportQuery(f: TxnFilters): Query {
  const { page: _page, ...rest } = f
  void _page
  return { ...rest, type: rest.type }
}
