import { Download, Paperclip, Pencil, Plus, Trash2, Upload } from 'lucide-react'
import { useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { toast } from 'sonner'

import { EmptyState, ErrorState, LoadingBlock, PageHeader, errorMessage } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { NativeSelect } from '@/components/ui/native-select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAccounts } from '@/features/accounts/api'
import { categoryOptions, useCategories } from '@/features/categories/api'
import { useFormatters } from '@/features/settings/usePreferences'
import { PAYMENT_METHOD_LABELS, TRANSACTION_TYPE_LABELS } from '@/lib/format'
import { cn } from '@/lib/utils'
import { download } from '@/services/api/client'
import type { TransactionOut } from '@/services/api/types'

import { DeleteTransactionDialog } from './DeleteTransactionDialog'
import { Receipts } from './Receipts'
import { TransactionFormDialog } from './TransactionFormDialog'
import { useTransactions } from './api'
import { type TxnFilters, filtersFromSearch, filtersToExportQuery, filtersToSearch } from './filters'

function FilterBar({ filters, onChange }: { filters: TxnFilters; onChange: (f: TxnFilters) => void }) {
  const accounts = useAccounts({ includeArchived: true })
  const cats = useCategories()
  const [q, setQ] = useState(filters.q ?? '')
  const [lastQ, setLastQ] = useState(filters.q)
  if (lastQ !== filters.q) {
    // Keep the search box in sync when the URL changes (e.g. "Clear").
    setLastQ(filters.q)
    setQ(filters.q ?? '')
  }
  const set = (patch: Partial<TxnFilters>) => onChange({ ...filters, ...patch, page: undefined })
  const field = (id: string, label: string, control: React.ReactNode) => (
    <div className="grid gap-1">
      <Label htmlFor={id} className="text-xs">{label}</Label>
      {control}
    </div>
  )
  const allCats = cats.data ? [...categoryOptions(cats.data, 'expense'), ...categoryOptions(cats.data, 'income')] : []
  return (
    <form role="search" aria-label="Filter transactions" className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4 xl:grid-cols-6"
      onSubmit={(e) => { e.preventDefault(); set({ q: q.trim() || undefined }) }}>
      {field('f-q', 'Search', <Input id="f-q" type="search" placeholder="Payee, description, notes" value={q}
        onChange={(e) => setQ(e.target.value)} onBlur={() => set({ q: q.trim() || undefined })} />)}
      {field('f-from', 'From', <Input id="f-from" type="date" value={filters.date_from ?? ''}
        onChange={(e) => set({ date_from: e.target.value || undefined })} />)}
      {field('f-to', 'To', <Input id="f-to" type="date" value={filters.date_to ?? ''}
        onChange={(e) => set({ date_to: e.target.value || undefined })} />)}
      {field('f-type', 'Type', (
        <NativeSelect id="f-type" value={filters.type?.[0] ?? ''} onChange={(e) => set({ type: e.target.value ? [e.target.value] : undefined })}>
          <option value="">All types</option>
          {Object.entries(TRANSACTION_TYPE_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </NativeSelect>
      ))}
      {field('f-account', 'Account', (
        <NativeSelect id="f-account" value={filters.account_id ?? ''} onChange={(e) => set({ account_id: e.target.value || undefined })}>
          <option value="">All accounts</option>
          {(accounts.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </NativeSelect>
      ))}
      {field('f-category', 'Category', (
        <NativeSelect id="f-category" value={filters.category_id ?? ''} onChange={(e) => set({ category_id: e.target.value || undefined })}>
          <option value="">All categories</option>
          {allCats.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
        </NativeSelect>
      ))}
      {field('f-method', 'Payment method', (
        <NativeSelect id="f-method" value={filters.payment_method ?? ''} onChange={(e) => set({ payment_method: e.target.value || undefined })}>
          <option value="">Any method</option>
          {Object.entries(PAYMENT_METHOD_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </NativeSelect>
      ))}
      {field('f-min', 'Min amount', <Input id="f-min" inputMode="decimal" value={filters.amount_min ?? ''}
        onChange={(e) => set({ amount_min: e.target.value || undefined })} />)}
      {field('f-max', 'Max amount', <Input id="f-max" inputMode="decimal" value={filters.amount_max ?? ''}
        onChange={(e) => set({ amount_max: e.target.value || undefined })} />)}
      {field('f-tag', 'Tag', <Input id="f-tag" value={filters.tag ?? ''} onChange={(e) => set({ tag: e.target.value || undefined })} />)}
      <div className="flex items-end gap-2">
        <Button type="submit" variant="secondary">Apply</Button>
        <Button type="button" variant="ghost" onClick={() => onChange({})}>Clear</Button>
      </div>
    </form>
  )
}

export function TransactionsPage() {
  const [params, setParams] = useSearchParams()
  const filters = filtersFromSearch(params)
  const query = useTransactions(filters)
  const { money, date } = useFormatters()
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState<TransactionOut | undefined>()
  const [deleting, setDeleting] = useState<TransactionOut | null>(null)
  const [receiptsFor, setReceiptsFor] = useState<string | null>(null)
  const setFilters = (f: TxnFilters) => setParams(filtersToSearch(f), { replace: true })
  const page = filters.page ?? 1
  const rows = query.data?.data ?? []
  const meta = query.data?.meta
  const receiptsTxn = rows.find((t) => t.id === receiptsFor)

  const exportCsv = () =>
    void download('/transactions/export.csv', filtersToExportQuery(filters), 'transactions.csv')
      .catch((err) => toast.error(errorMessage(err)))

  return (
    <div>
      <PageHeader
        title="Transactions"
        description="Every money movement across your accounts."
        actions={<>
          <Button variant="outline" onClick={exportCsv}><Download aria-hidden /> Export CSV</Button>
          <Button variant="outline" asChild><Link to="/transactions/import"><Upload aria-hidden /> Import CSV</Link></Button>
          <Button onClick={() => { setEditing(undefined); setFormOpen(true) }}><Plus aria-hidden /> Add transaction</Button>
        </>}
      />
      <FilterBar filters={filters} onChange={setFilters} />
      {meta && (
        <p className="mb-2 text-sm text-muted-foreground" aria-live="polite">
          {meta.total_items} transaction{meta.total_items === 1 ? '' : 's'} · Expenses {money(meta.totals.net_expense)} · Income {money(meta.totals.income)}
        </p>
      )}
      {query.isPending ? (
        <LoadingBlock label="Loading transactions" />
      ) : query.isError ? (
        <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      ) : rows.length === 0 ? (
        <EmptyState title="No transactions found"
          description={params.size ? 'Try changing or clearing the filters.' : 'Add your first income or expense to get started.'}
          action={<Button onClick={() => { setEditing(undefined); setFormOpen(true) }}>Add transaction</Button>} />
      ) : (
        <div className="overflow-x-auto rounded-md border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Category</TableHead>
                <TableHead>Account</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead><span className="sr-only">Actions</span></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((t) => {
                const sign = t.type === 'income' || t.type === 'refund' ? '+' : t.type === 'expense' ? '−' : ''
                return (
                  <TableRow key={t.id}>
                    <TableCell className="whitespace-nowrap">{date(t.txn_date)}</TableCell>
                    <TableCell className="max-w-64">
                      <p className="truncate">{t.description ?? t.payee ?? TRANSACTION_TYPE_LABELS[t.type]}</p>
                      <p className="text-xs text-muted-foreground">
                        {TRANSACTION_TYPE_LABELS[t.type]}{t.payment_method ? ` · ${PAYMENT_METHOD_LABELS[t.payment_method]}` : ''}
                        {t.tags.map((tag) => <Badge key={tag} variant="secondary" className="ml-1 text-[10px]">{tag}</Badge>)}
                      </p>
                    </TableCell>
                    <TableCell>{t.parent_category_name ? `${t.parent_category_name} › ${t.category_name}` : t.category_name ?? '—'}</TableCell>
                    <TableCell className="whitespace-nowrap">{t.type === 'transfer' ? `${t.account_name} → ${t.counter_account_name}` : t.account_name}</TableCell>
                    <TableCell className={cn('text-right whitespace-nowrap tabular-nums',
                      t.type === 'income' || t.type === 'refund' ? 'text-success' : t.type === 'expense' ? '' : 'text-muted-foreground')}>
                      {sign}{money(t.amount)}
                    </TableCell>
                    <TableCell className="whitespace-nowrap text-right">
                      <Button variant="ghost" size="icon-sm" aria-label={`Receipts for ${t.description ?? 'transaction'} (${t.attachments.length})`}
                        onClick={() => setReceiptsFor(t.id)}>
                        <Paperclip aria-hidden />{t.attachments.length > 0 && <span className="text-xs">{t.attachments.length}</span>}
                      </Button>
                      <Button variant="ghost" size="icon-sm" aria-label={`Edit ${t.description ?? 'transaction'}`} onClick={() => { setEditing(t); setFormOpen(true) }}>
                        <Pencil aria-hidden />
                      </Button>
                      <Button variant="ghost" size="icon-sm" aria-label={`Delete ${t.description ?? 'transaction'}`} onClick={() => setDeleting(t)}>
                        <Trash2 aria-hidden />
                      </Button>
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </div>
      )}
      {meta && meta.total_pages > 1 && (
        <nav aria-label="Pagination" className="mt-4 flex items-center justify-between gap-2">
          <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setFilters({ ...filters, page: page - 1 })}>Previous</Button>
          <span className="text-sm">Page {page} of {meta.total_pages}</span>
          <Button variant="outline" size="sm" disabled={page >= meta.total_pages} onClick={() => setFilters({ ...filters, page: page + 1 })}>Next</Button>
        </nav>
      )}
      <TransactionFormDialog open={formOpen} onOpenChange={setFormOpen} transaction={editing} />
      <DeleteTransactionDialog transaction={deleting} onClose={() => setDeleting(null)} />
      <Dialog open={!!receiptsTxn} onOpenChange={(o) => !o && setReceiptsFor(null)}>
        <DialogContent>
          <DialogHeader><DialogTitle>Receipts</DialogTitle></DialogHeader>
          {receiptsTxn && <Receipts transaction={receiptsTxn} />}
        </DialogContent>
      </Dialog>
    </div>
  )
}
