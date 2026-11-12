import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type {
  LoanCreate,
  LoanEventCreate,
  LoanEventOut,
  LoanOut,
  LoanPaymentCreate,
  LoanPaymentOut,
  LoanScheduleOut,
  LoanSimulateOut,
  LoanSimulateRequest,
  LoanSummaryOut,
  LoanUpdate,
} from '@/services/api/types'

export function useLoans(status?: string) {
  return useQuery({
    queryKey: [...qk.loans, status ?? 'all'],
    queryFn: () =>
      api.get<LoanOut[]>('/loans', status && status !== 'all' ? { status } : undefined),
  })
}

export function useLoanSummary() {
  return useQuery({
    queryKey: [...qk.loans, 'summary'],
    queryFn: () => api.get<LoanSummaryOut>('/loans/summary'),
  })
}

export function useLoan(id: string) {
  return useQuery({
    queryKey: [...qk.loans, id],
    queryFn: () => api.get<LoanOut>(`/loans/${id}`),
    enabled: Boolean(id),
  })
}

export function useLoanSchedule(id: string) {
  return useQuery({
    queryKey: [...qk.loans, id, 'schedule'],
    queryFn: () => api.get<LoanScheduleOut>(`/loans/${id}/schedule`),
    enabled: Boolean(id),
  })
}

export function useCreateLoan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LoanCreate) => api.post<LoanOut>('/loans', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useUpdateLoan(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LoanUpdate) => api.patch<LoanOut>(`/loans/${id}`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useDeleteLoan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.del(`/loans/${id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useRecordPayment(loanId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LoanPaymentCreate) =>
      api.post<LoanPaymentOut>(`/loans/${loanId}/payments`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.accounts })
      qc.invalidateQueries({ queryKey: qk.transactions })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useAddLoanEvent(loanId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LoanEventCreate) =>
      api.post<LoanEventOut>(`/loans/${loanId}/events`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useSimulateLoan(loanId: string) {
  return useMutation({
    mutationFn: (data: LoanSimulateRequest) =>
      api.post<LoanSimulateOut>(`/loans/${loanId}/simulate`, data),
  })
}

