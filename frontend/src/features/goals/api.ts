import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type {
  GoalContributionCreate,
  GoalContributionOut,
  GoalCreate,
  GoalOut,
  GoalUpdate,
  SavingsTargetIn,
  SavingsTargetOut,
} from '@/services/api/types'

export function useSavingsTarget(month?: string) {
  return useQuery({
    queryKey: [...qk.savingsTargets, month ?? 'current'],
    queryFn: () =>
      api.get<SavingsTargetOut>('/savings-targets', month ? { month } : undefined),
  })
}

export function useSetSavingsTarget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ effectiveFrom, data }: { effectiveFrom: string; data: SavingsTargetIn }) =>
      api.put<SavingsTargetOut>(`/savings-targets/${effectiveFrom}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.savingsTargets })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useGoals(status?: string) {
  return useQuery({
    queryKey: [...qk.goals, status ?? 'all'],
    queryFn: () =>
      api.get<GoalOut[]>('/goals', status && status !== 'all' ? { status } : undefined),
  })
}

export function useCreateGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalCreate) => api.post<GoalOut>('/goals', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.goals })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useUpdateGoal(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: GoalUpdate) => api.patch<GoalOut>(`/goals/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.goals })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useDeleteGoal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.del(`/goals/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.goals })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useGoalContributions(goalId: string) {
  return useQuery({
    queryKey: [...qk.goals, goalId, 'contributions'],
    queryFn: () => api.get<GoalContributionOut[]>(`/goals/${goalId}/contributions`),
    enabled: Boolean(goalId),
  })
}

export function useAddContribution(goalId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      kind,
      data,
    }: {
      kind: 'contribution' | 'withdrawal'
      data: GoalContributionCreate
    }) => {
      const path =
        kind === 'withdrawal'
          ? `/goals/${goalId}/withdrawals`
          : `/goals/${goalId}/contributions`
      return api.post<GoalContributionOut>(path, data)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.goals })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useDeleteContribution(goalId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (contributionId: string) =>
      api.del(`/goals/${goalId}/contributions/${contributionId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.goals })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

