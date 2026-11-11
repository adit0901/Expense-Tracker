import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { FormField } from '@/components/common/FormField'
import { PeriodFilter } from '@/components/common/PeriodFilter'
import { PageHeader, errorMessage } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { useAccounts } from '@/features/accounts/api'
import { categoryOptions, useCategories } from '@/features/categories/api'
import { useIncomeSources } from '@/features/transactions/api'
import { usePeriodParam } from '@/lib/period'
import { qk } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type { IncomeSourceOut } from '@/services/api/types'

import { IncomeReportView } from './views'

const SOURCE_TYPES = ['salary', 'bonus', 'freelance', 'business', 'rental', 'dividend', 'interest', 'other'] as const

function SourceDialog({ source, open, onClose }: { source?: IncomeSourceOut; open: boolean; onClose: () => void }) {
  const qc = useQueryClient()
  const cats = useCategories()
  const accounts = useAccounts()
  const [name, setName] = useState(source?.name ?? '')
  const [type, setType] = useState<string>(source?.type ?? 'salary')
  const [categoryId, setCategoryId] = useState(source?.default_category_id ?? '')
  const [accountId, setAccountId] = useState(source?.default_account_id ?? '')
  const [error, setError] = useState<string | null>(null)
  const save = useMutation({
    mutationFn: () => {
      const body = { name, type, default_category_id: categoryId || null, default_account_id: accountId || null }
      return source ? api.patch(`/income-sources/${source.id}`, body) : api.post('/income-sources', body)
    },
    onSuccess: async () => {
      await qc.invalidateQueries({ queryKey: qk.incomeSources })
      toast.success('Income source saved')
      onClose()
    },
    onError: (err) => setError(errorMessage(err)),
  })
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader><DialogTitle>{source ? 'Edit income source' : 'Add income source'}</DialogTitle></DialogHeader>
        <form className="grid gap-4" noValidate onSubmit={(e) => { e.preventDefault(); save.mutate() }}>
          {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
          <FormField label="Name">{(p) => <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="Acme Corp Salary" {...p} />}</FormField>
          <FormField label="Type">{(p) => (
            <NativeSelect value={type} onChange={(e) => setType(e.target.value)} {...p}>
              {SOURCE_TYPES.map((t) => <option key={t} value={t}>{t[0]!.toUpperCase() + t.slice(1)}</option>)}
            </NativeSelect>
          )}</FormField>
          <FormField label="Default category (optional)">{(p) => (
            <NativeSelect value={categoryId} onChange={(e) => setCategoryId(e.target.value)} {...p}>
              <option value="">None</option>
              {(cats.data ? categoryOptions(cats.data, 'income') : []).map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
            </NativeSelect>
          )}</FormField>
          <FormField label="Default receiving account (optional)">{(p) => (
            <NativeSelect value={accountId} onChange={(e) => setAccountId(e.target.value)} {...p}>
              <option value="">None</option>
              {(accounts.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </NativeSelect>
          )}</FormField>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={!name.trim() || save.isPending}>Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function IncomeSources() {
  const qc = useQueryClient()
  const sources = useIncomeSources(true)
  const [editing, setEditing] = useState<IncomeSourceOut | undefined>()
  const [open, setOpen] = useState(false)
  const toggle = useMutation({
    mutationFn: (s: IncomeSourceOut) => api.patch(`/income-sources/${s.id}`, { is_active: !s.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.incomeSources }),
    onError: (err) => toast.error(errorMessage(err)),
  })
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle><h2 className="text-base">Income sources</h2></CardTitle>
        <Button size="sm" onClick={() => { setEditing(undefined); setOpen(true) }}><Plus aria-hidden /> Add source</Button>
      </CardHeader>
      <CardContent>
        {sources.data?.length === 0 && <p className="text-sm text-muted-foreground">Add sources like your employer or freelance clients to report income separately.</p>}
        <ul className="divide-y">
          {sources.data?.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
              <span className="flex-1">{s.name} <span className="text-muted-foreground">· {s.type}</span></span>
              {!s.is_active && <Badge variant="secondary">Inactive</Badge>}
              <Button variant="ghost" size="sm" onClick={() => { setEditing(s); setOpen(true) }}>Edit</Button>
              <Button variant="ghost" size="sm" onClick={() => toggle.mutate(s)}>{s.is_active ? 'Deactivate' : 'Activate'}</Button>
            </li>
          ))}
        </ul>
      </CardContent>
      {open && <SourceDialog key={editing?.id ?? 'new'} source={editing} open={open} onClose={() => setOpen(false)} />}
    </Card>
  )
}

export function IncomePage() {
  const { query, ready } = usePeriodParam('this_year')
  return (
    <div className="grid gap-6">
      <PageHeader title="Income" description="Income by source and category, with salary gross, deductions and net."
        actions={<PeriodFilter defaultKind="this_year" />} />
      <IncomeReportView query={query} enabled={ready} />
      <IncomeSources />
    </div>
  )
}
