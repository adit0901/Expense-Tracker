import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Lock, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { FormField } from '@/components/common/FormField'
import { ErrorState, LoadingBlock, errorMessage } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { invalidateFinancials, qk } from '@/lib/queryKeys'
import { ApiError, api } from '@/services/api/client'
import type { CategoryKind, CategoryOut } from '@/services/api/types'

import { categoryOptions, categoryTree, useCategories } from './api'

interface Editing {
  kind: CategoryKind
  parent?: CategoryOut
  category?: CategoryOut
}

function CategoryDialog({ editing, onClose }: { editing: Editing | null; onClose: () => void }) {
  const qc = useQueryClient()
  const [name, setName] = useState('')
  const [color, setColor] = useState('#1d4ed8')
  const [error, setError] = useState<string | null>(null)
  const [lastKey, setLastKey] = useState<string>('')
  const key = editing ? `${editing.category?.id ?? 'new'}:${editing.parent?.id ?? ''}` : ''
  if (key !== lastKey) {
    setLastKey(key)
    setName(editing?.category?.name ?? '')
    setColor(editing?.category?.color ?? '#1d4ed8')
    setError(null)
  }
  const save = useMutation({
    mutationFn: () => {
      if (editing?.category) return api.patch(`/categories/${editing.category.id}`, { name, color })
      return api.post('/categories', { kind: editing?.kind, name, color, parent_id: editing?.parent?.id ?? null })
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: qk.categories })
      toast.success(editing?.category ? 'Category updated' : 'Category created')
      onClose()
    },
    onError: (err) => setError(errorMessage(err)),
  })
  const title = editing?.category ? 'Edit category' : editing?.parent ? `Add subcategory under ${editing.parent.name}` : 'Add category'
  return (
    <Dialog open={!!editing} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader><DialogTitle>{title}</DialogTitle></DialogHeader>
        <form className="grid gap-4" noValidate onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
          <FormField label="Name" error={error ?? undefined}>
            {(p) => <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={60} {...p}
              disabled={!!editing?.category?.is_system} />}
          </FormField>
          <FormField label="Colour">
            {(p) => <Input type="color" className="h-10 w-20 p-1" value={color} onChange={(e) => setColor(e.target.value)} {...p} />}
          </FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={!name.trim() || save.isPending}>Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DeleteCategoryDialog({ category, all, onClose }: { category: CategoryOut | null; all: CategoryOut[]; onClose: () => void }) {
  const qc = useQueryClient()
  const [replacement, setReplacement] = useState<string>('')
  const [needsReplacement, setNeedsReplacement] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const remove = useMutation({
    mutationFn: () => api.del(`/categories/${category?.id}`, { replacement_id: replacement || undefined }),
    onSuccess: async () => {
      await Promise.all([qc.invalidateQueries({ queryKey: qk.categories }), invalidateFinancials(qc)])
      toast.success('Category deleted')
      close()
    },
    onError: (err) => {
      if (err instanceof ApiError && err.code === 'category_in_use') {
        setNeedsReplacement(true)
        setError('This category has transactions. Choose a category to move them to.')
      } else setError(errorMessage(err))
    },
  })
  const close = () => {
    setReplacement('')
    setNeedsReplacement(false)
    setError(null)
    onClose()
  }
  const excluded = new Set([category?.id, ...all.filter((c) => c.parent_id === category?.id).map((c) => c.id)])
  const options = category ? categoryOptions(all, category.kind).filter((o) => !excluded.has(o.value)) : []
  return (
    <ConfirmDialog
      open={!!category}
      onOpenChange={(o) => !o && close()}
      title={`Delete ${category?.name ?? 'category'}?`}
      description="Its subcategories are deleted too. Transactions are never deleted; they move to the replacement."
      confirmLabel={needsReplacement ? 'Move transactions and delete' : 'Delete'}
      pending={remove.isPending || (needsReplacement && !replacement)}
      onConfirm={() => remove.mutate()}
    >
      {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
      {needsReplacement && (
        <FormField label="Replacement category">
          {(p) => (
            <NativeSelect value={replacement} onChange={(e) => setReplacement(e.target.value)} {...p}>
              <option value="">Choose a category</option>
              {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </NativeSelect>
          )}
        </FormField>
      )}
    </ConfirmDialog>
  )
}

function CategoryList({ kind, all }: { kind: CategoryKind; all: CategoryOut[] }) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState<Editing | null>(null)
  const [deleting, setDeleting] = useState<CategoryOut | null>(null)
  const toggle = useMutation({
    mutationFn: (c: CategoryOut) => api.patch(`/categories/${c.id}`, { is_essential: !c.is_essential }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.categories }),
    onError: (err) => toast.error(errorMessage(err)),
  })
  const tree = categoryTree(all, kind)

  const row = (c: CategoryOut, depth: number) => (
    <li key={c.id} className="flex flex-wrap items-center gap-2 border-b py-2" style={{ paddingLeft: depth * 24 }}>
      <span className="size-3 shrink-0 rounded-full" style={{ backgroundColor: c.color ?? 'var(--chart-other)' }} aria-hidden />
      <span className="min-w-0 flex-1 truncate">{c.name}</span>
      {c.is_system && <Badge variant="outline"><Lock className="size-3" aria-hidden /> System</Badge>}
      {kind === 'expense' && (
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Switch checked={c.is_essential} onCheckedChange={() => toggle.mutate(c)} aria-label={`${c.name} is essential`} />
          Essential
        </span>
      )}
      {depth === 0 && (
        <Button variant="ghost" size="icon-sm" aria-label={`Add subcategory under ${c.name}`} onClick={() => setEditing({ kind, parent: c })}>
          <Plus aria-hidden />
        </Button>
      )}
      <Button variant="ghost" size="icon-sm" aria-label={`Edit ${c.name}`} onClick={() => setEditing({ kind, category: c })}>
        <Pencil aria-hidden />
      </Button>
      {!c.is_system && (
        <Button variant="ghost" size="icon-sm" aria-label={`Delete ${c.name}`} onClick={() => setDeleting(c)}>
          <Trash2 aria-hidden />
        </Button>
      )}
    </li>
  )

  return (
    <div>
      <div className="mb-2 flex justify-end">
        <Button size="sm" onClick={() => setEditing({ kind })}><Plus aria-hidden /> Add {kind} category</Button>
      </div>
      <ul aria-label={`${kind} categories`}>
        {tree.map((t) => [row(t, 0), ...t.children.map((c) => row(c, 1))])}
      </ul>
      <CategoryDialog editing={editing} onClose={() => setEditing(null)} />
      <DeleteCategoryDialog category={deleting} all={all} onClose={() => setDeleting(null)} />
    </div>
  )
}

export function CategoriesPage() {
  const cats = useCategories()
  if (cats.isPending) return <LoadingBlock label="Loading categories" />
  if (cats.isError) return <ErrorState error={cats.error} onRetry={() => void cats.refetch()} />
  return (
    <Tabs defaultValue="expense" className="max-w-2xl">
      <TabsList>
        <TabsTrigger value="expense">Expense</TabsTrigger>
        <TabsTrigger value="income">Income</TabsTrigger>
      </TabsList>
      <TabsContent value="expense"><CategoryList kind="expense" all={cats.data} /></TabsContent>
      <TabsContent value="income"><CategoryList kind="income" all={cats.data} /></TabsContent>
    </Tabs>
  )
}
