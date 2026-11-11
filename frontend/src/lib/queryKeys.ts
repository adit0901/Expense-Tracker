import type { QueryClient } from '@tanstack/react-query'

export const qk = {
  accounts: ['accounts'] as const,
  accountsSummary: ['accounts', 'summary'] as const,
  categories: ['categories'] as const,
  incomeSources: ['income-sources'] as const,
  transactions: ['transactions'] as const,
  dashboard: ['dashboard'] as const,
  reports: ['reports'] as const,
  imports: ['imports'] as const,
}

/** After any change to money movements, refresh everything derived from them. */
export function invalidateFinancials(qc: QueryClient): Promise<void> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: qk.transactions }),
    qc.invalidateQueries({ queryKey: qk.accounts }),
    qc.invalidateQueries({ queryKey: qk.dashboard }),
    qc.invalidateQueries({ queryKey: qk.reports }),
  ]).then(() => undefined)
}
