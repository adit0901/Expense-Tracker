import { useQuery } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type { AccountOut, AccountsSummary, Page } from '@/services/api/types'

export function useAccounts(opts: { includeArchived?: boolean } = {}) {
  return useQuery({
    queryKey: [...qk.accounts, 'list', !!opts.includeArchived],
    queryFn: async () =>
      (await api.page<Page<AccountOut>>('/accounts', { page_size: 100, include_archived: !!opts.includeArchived })).data,
  })
}

export function useAccountsSummary() {
  return useQuery({ queryKey: qk.accountsSummary, queryFn: () => api.get<AccountsSummary>('/accounts/summary') })
}
