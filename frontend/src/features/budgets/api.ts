import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type {
  BudgetAlertResponse,
  BudgetComparisonResponse,
  BudgetResponse,
  SetBudgetRequest,
} from '@/services/api/types'

export function useBudget(month: string) {
  return useQuery({
    queryKey: [...qk.budgets, month],
    queryFn: () => api.get<BudgetResponse>('/budgets', { month }),
    enabled: Boolean(month),
  })
}

export function useSetBudget(month: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: SetBudgetRequest) => api.put<BudgetResponse>(`/budgets/${month}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.budgets })
      qc.invalidateQueries({ queryKey: qk.budgetAlerts })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useCopyBudget(targetMonth: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceMonth: string) =>
      api.post<BudgetResponse>(`/budgets/${targetMonth}/copy-from/${sourceMonth}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.budgets })
      qc.invalidateQueries({ queryKey: qk.budgetAlerts })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useBudgetComparison(months = 6, categoryId?: string) {
  return useQuery({
    queryKey: [...qk.budgets, 'comparison', months, categoryId ?? 'all'],
    queryFn: () =>
      api.get<BudgetComparisonResponse>('/budgets/comparison', {
        months,
        category_id: categoryId || undefined,
      }),
  })
}

export function useBudgetAlerts(month?: string) {
  return useQuery({
    queryKey: [...qk.budgetAlerts, month ?? 'all'],
    queryFn: () => api.get<BudgetAlertResponse[]>('/budget-alerts', month ? { month } : undefined),
  })
}

