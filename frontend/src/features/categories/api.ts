import { useQuery } from '@tanstack/react-query'

import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type { CategoryKind, CategoryOut, Page } from '@/services/api/types'

export function useCategories() {
  return useQuery({
    queryKey: qk.categories,
    queryFn: async () => (await api.page<Page<CategoryOut>>('/categories', { page_size: 100 })).data,
    staleTime: 60_000,
  })
}

export interface CategoryNode extends CategoryOut {
  children: CategoryOut[]
}

export function categoryTree(all: CategoryOut[], kind: CategoryKind): CategoryNode[] {
  const tops = all.filter((c) => c.kind === kind && !c.parent_id).sort((a, b) => a.name.localeCompare(b.name))
  return tops.map((t) => ({
    ...t,
    children: all.filter((c) => c.parent_id === t.id).sort((a, b) => a.name.localeCompare(b.name)),
  }))
}

/** Flat options with subcategories labelled "Parent › Child". */
export function categoryOptions(all: CategoryOut[], kind: CategoryKind): { value: string; label: string }[] {
  return categoryTree(all, kind).flatMap((t) => [
    { value: t.id, label: t.name },
    ...t.children.map((c) => ({ value: c.id, label: `${t.name} › ${c.name}` })),
  ])
}
