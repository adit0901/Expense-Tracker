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

import {
  getScenarioLoan,
  getScenarioLoans,
  getScenarioSchedule,
  getScenarioSummary,
  WORST_LOANS,
} from './test-scenarios'
import { useBreakUIScenario } from './useBreakUIScenario'

export function useLoans(status?: string) {
  const scenario = useBreakUIScenario()
  return useQuery({
    queryKey: [...qk.loans, status ?? 'all', scenario],
    queryFn: () => {
      if (scenario) {
        return Promise.resolve(getScenarioLoans(scenario, status))
      }
      return api.get<LoanOut[]>('/loans', status && status !== 'all' ? { status } : undefined)
    },
  })
}

export function useLoanSummary() {
  const scenario = useBreakUIScenario()
  return useQuery({
    queryKey: [...qk.loans, 'summary', scenario],
    queryFn: () => {
      if (scenario) {
        return Promise.resolve(getScenarioSummary(scenario))
      }
      return api.get<LoanSummaryOut>('/loans/summary')
    },
  })
}

export function useLoan(id: string) {
  const scenario = useBreakUIScenario()
  return useQuery({
    queryKey: [...qk.loans, id, scenario],
    queryFn: () => {
      if (scenario) {
        const item = getScenarioLoan(id, scenario)
        if (item) return Promise.resolve(item)
      }
      return api.get<LoanOut>(`/loans/${id}`)
    },
    enabled: Boolean(id),
  })
}

export function useLoanSchedule(id: string) {
  const scenario = useBreakUIScenario()
  return useQuery({
    queryKey: [...qk.loans, id, 'schedule', scenario],
    queryFn: () => {
      if (scenario) {
        return Promise.resolve(getScenarioSchedule(id, scenario))
      }
      return api.get<LoanScheduleOut>(`/loans/${id}/schedule`)
    },
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
  const scenario = useBreakUIScenario()
  return useMutation({
    mutationFn: (id: string) => {
      if (scenario) {
        return Promise.resolve({ success: true })
      }
      return api.del(`/loans/${id}`)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useRecordPayment(loanId: string) {
  const qc = useQueryClient()
  const scenario = useBreakUIScenario()
  return useMutation({
    mutationFn: (data: LoanPaymentCreate) => {
      if (scenario) {
        const amountNum = typeof data.amount === 'string' ? parseFloat(data.amount) : 0
        const out: LoanPaymentOut = {
          id: `payment-${Date.now()}`,
          loan_id: loanId,
          account_id: data.account_id ?? '00000000-0000-0000-0000-000000000000',
          transaction_id: `tx-${Date.now()}`,
          payment_date: data.payment_date,
          principal: (amountNum * 0.7).toFixed(2),
          interest: (amountNum * 0.3).toFixed(2),
          total_amount: String(data.amount ?? '0.00'),
          current_outstanding: '10000.00',
          installment_no: 1,
          created_at: new Date().toISOString(),
        }
        return Promise.resolve(out)
      }
      return api.post<LoanPaymentOut>(`/loans/${loanId}/payments`, data)
    },
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
  const scenario = useBreakUIScenario()
  return useMutation({
    mutationFn: (data: LoanEventCreate) => {
      if (scenario) {
        const out: LoanEventOut = {
          id: `event-${Date.now()}`,
          loan_id: loanId,
          kind: data.kind,
          effective_date: data.effective_date,
          payload: data.payload ?? {},
          created_at: new Date().toISOString(),
        }
        return Promise.resolve(out)
      }
      return api.post<LoanEventOut>(`/loans/${loanId}/events`, data)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.loans })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useSimulateLoan(loanId: string) {
  const scenario = useBreakUIScenario()
  return useMutation({
    mutationFn: (data: LoanSimulateRequest) => {
      if (scenario) {
        const loan: LoanOut = getScenarioLoan(loanId, scenario) ?? WORST_LOANS[0]!
        const currentEmi = loan.emi_amount
        const currentOutstanding = parseFloat(loan.current_outstanding) || 100000
        const prepayAmount = parseFloat(String(data.amount ?? '0'))
        const simulatedOutstanding = Math.max(0, currentOutstanding - prepayAmount)
        const newTenure = Math.max(1, Math.round(loan.remaining_installments * 0.75))
        const simulatedEmi = (simulatedOutstanding / newTenure).toFixed(2)
        const interestSaved = ((parseFloat(loan.remaining_interest) || 50000) * 0.25).toFixed(2)

        return Promise.resolve({
          current_emi: currentEmi,
          current_end_date: loan.end_date,
          current_tenure_months: loan.remaining_installments,
          current_total_interest: loan.remaining_interest || '50000.00',
          interest_saved: interestSaved,
          simulated_emi: simulatedEmi,
          simulated_end_date: '2028-06-01',
          simulated_tenure_months: newTenure,
          simulated_total_interest: (
            (parseFloat(loan.remaining_interest) || 50000) - parseFloat(interestSaved)
          ).toFixed(2),
          tenure_months_saved: loan.remaining_installments - newTenure,
        })
      }
      return api.post<LoanSimulateOut>(`/loans/${loanId}/simulate`, data)
    },
  })
}
