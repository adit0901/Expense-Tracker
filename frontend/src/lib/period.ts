import { useSearchParams } from 'react-router'

export type PeriodKind = 'this_month' | 'last_month' | 'this_quarter' | 'this_year' | 'this_fy' | 'custom'

export const PERIOD_OPTIONS: { value: PeriodKind; label: string }[] = [
  { value: 'this_month', label: 'This month' },
  { value: 'last_month', label: 'Last month' },
  { value: 'this_quarter', label: 'This quarter' },
  { value: 'this_year', label: 'This year' },
  { value: 'this_fy', label: 'This financial year' },
  { value: 'custom', label: 'Custom range' },
]

export interface PeriodQuery {
  period: PeriodKind
  start?: string
  end?: string
  [key: string]: string | undefined
}

const KINDS = new Set(PERIOD_OPTIONS.map((o) => o.value))

/** Period selection kept in the URL so it survives reloads and can be shared. */
export function usePeriodParam(defaultKind: PeriodKind = 'this_month') {
  const [params, setParams] = useSearchParams()
  const raw = params.get('period') as PeriodKind | null
  const period: PeriodKind = raw && KINDS.has(raw) ? raw : defaultKind
  const start = params.get('start') ?? undefined
  const end = params.get('end') ?? undefined
  const ready = period !== 'custom' || (!!start && !!end && start <= end)
  const query: PeriodQuery = period === 'custom' ? { period, start, end } : { period }

  const setPeriod = (next: PeriodKind, range?: { start?: string; end?: string }) => {
    const p = new URLSearchParams(params)
    p.set('period', next)
    if (next === 'custom') {
      if (range?.start) p.set('start', range.start)
      if (range?.end) p.set('end', range.end)
    } else {
      p.delete('start')
      p.delete('end')
    }
    setParams(p, { replace: true })
  }
  return { period, start, end, query, ready, setPeriod }
}
