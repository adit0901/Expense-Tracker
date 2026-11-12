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
  budgets: ['budgets'] as const,
  budgetAlerts: ['budget-alerts'] as const,
  savingsTargets: ['savings-targets'] as const,
  goals: ['goals'] as const,
  assets: ['assets'] as const,
  liabilities: ['liabilities'] as const,
  loans: ['loans'] as const,
  netWorth: ['net-worth'] as const,
}

/** After any change to money movements, refresh everything derived from them. */
export function invalidateFinancials(qc: QueryClient): Promise<void> {
  return Promise.all([
    qc.invalidateQueries({ queryKey: qk.transactions }),
    qc.invalidateQueries({ queryKey: qk.accounts }),
    qc.invalidateQueries({ queryKey: qk.dashboard }),
    qc.invalidateQueries({ queryKey: qk.reports }),
    qc.invalidateQueries({ queryKey: qk.budgets }),
    qc.invalidateQueries({ queryKey: qk.budgetAlerts }),
    qc.invalidateQueries({ queryKey: qk.savingsTargets }),
    qc.invalidateQueries({ queryKey: qk.goals }),
    qc.invalidateQueries({ queryKey: qk.netWorth }),
    qc.invalidateQueries({ queryKey: qk.loans }),
  ]).then(() => undefined)
}
