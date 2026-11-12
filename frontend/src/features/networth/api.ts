import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type {
  AssetCloseIn,
  AssetCreate,
  AssetOut,
  AssetValuationIn,
  AssetValuationOut,
  LiabilityBalanceIn,
  LiabilityBalanceOut,
  LiabilityCloseIn,
  LiabilityCreate,
  LiabilityOut,
  NetWorthOut,
  NetWorthSnapshotOut,
} from '@/services/api/types'

export function useNetWorth(asOf?: string) {
  return useQuery({
    queryKey: [...qk.netWorth, asOf ?? 'current'],
    queryFn: () => api.get<NetWorthOut>('/net-worth', asOf ? { as_of: asOf } : undefined),
  })
}

export function useNetWorthSnapshots() {
  return useQuery({
    queryKey: [...qk.netWorth, 'snapshots'],
    queryFn: () => api.get<NetWorthSnapshotOut[]>('/net-worth/snapshots'),
  })
}

export function useRecomputeSnapshot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (asOf: string) =>
      api.post<NetWorthSnapshotOut>(`/net-worth/snapshots/${asOf}/recompute`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useTakeSnapshot() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (asOf?: string) =>
      api.post<NetWorthSnapshotOut>('/net-worth/snapshots', asOf ? { as_of: asOf } : {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useAssets(includeClosed = false) {
  return useQuery({
    queryKey: [...qk.assets, includeClosed],
    queryFn: () => api.get<AssetOut[]>('/assets', { include_closed: includeClosed }),
  })
}

export function useCreateAsset() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssetCreate) => api.post<AssetOut>('/assets', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useAddAssetValuation(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssetValuationIn) =>
      api.post<AssetValuationOut>(`/assets/${assetId}/valuations`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useAssetValuations(assetId: string) {
  return useQuery({
    queryKey: [...qk.assets, assetId, 'valuations'],
    queryFn: () => api.get<AssetValuationOut[]>(`/assets/${assetId}/valuations`),
    enabled: Boolean(assetId),
  })
}

export function useCloseAsset(assetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AssetCloseIn) =>
      api.post<AssetOut>(`/assets/${assetId}/close`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.assets })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useLiabilities(includeClosed = false) {
  return useQuery({
    queryKey: [...qk.liabilities, includeClosed],
    queryFn: () => api.get<LiabilityOut[]>('/liabilities', { include_closed: includeClosed }),
  })
}

export function useCreateLiability() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LiabilityCreate) => api.post<LiabilityOut>('/liabilities', data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.liabilities })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useAddLiabilityBalance(liabilityId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LiabilityBalanceIn) =>
      api.post<LiabilityBalanceOut>(`/liabilities/${liabilityId}/balances`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.liabilities })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

export function useLiabilityBalances(liabilityId: string) {
  return useQuery({
    queryKey: [...qk.liabilities, liabilityId, 'balances'],
    queryFn: () => api.get<LiabilityBalanceOut[]>(`/liabilities/${liabilityId}/balances`),
    enabled: Boolean(liabilityId),
  })
}

export function useCloseLiability(liabilityId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: LiabilityCloseIn) =>
      api.post<LiabilityOut>(`/liabilities/${liabilityId}/close`, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: qk.liabilities })
      qc.invalidateQueries({ queryKey: qk.netWorth })
      qc.invalidateQueries({ queryKey: qk.dashboard })
    },
  })
}

