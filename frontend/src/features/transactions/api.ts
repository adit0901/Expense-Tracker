import { keepPreviousData, useQuery } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type { IncomeSourceOut, Page, PageMeta, TransactionOut, TransactionTotals } from '@/services/api/types'

import { type TxnFilters, filtersToApiQuery } from './filters'

export type TxnPage = Page<TransactionOut, PageMeta & { totals: TransactionTotals }>

export function useTransactions(filters: TxnFilters, pageSize = 25) {
  return useQuery({
    queryKey: [...qk.transactions, 'list', filters, pageSize],
    queryFn: () => api.page<TxnPage>('/transactions', filtersToApiQuery(filters, pageSize)),
    placeholderData: keepPreviousData,
  })
}

export function useIncomeSources(includeInactive = false) {
  return useQuery({
    queryKey: [...qk.incomeSources, includeInactive],
    queryFn: async () =>
      (await api.page<Page<IncomeSourceOut>>('/income-sources', { page_size: 100, include_inactive: includeInactive })).data,
  })
}
