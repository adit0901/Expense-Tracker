import { useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { PageHeader, Spinner, errorMessage } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { NativeSelect } from '@/components/ui/native-select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useAccounts } from '@/features/accounts/api'
import { useFormatters } from '@/features/settings/usePreferences'
import { invalidateFinancials } from '@/lib/queryKeys'
import { ApiError, api } from '@/services/api/client'
import type { ImportBatchOut } from '@/services/api/types'

const DATE_FORMATS = ['DD/MM/YYYY', 'MM/DD/YYYY', 'YYYY-MM-DD', 'DD-MM-YYYY', 'DD-MMM-YYYY', 'DD/MM/YY']
const MAPPING_FIELDS: { key: string; label: string }[] = [
  { key: 'date', label: 'Date' },
  { key: 'amount', label: 'Amount (signed or with type)' },
  { key: 'type', label: 'Type (income/expense, Dr/Cr)' },
  { key: 'debit', label: 'Debit / withdrawal' },
  { key: 'credit', label: 'Credit / deposit' },
  { key: 'description', label: 'Description' },
  { key: 'payee', label: 'Payee' },
  { key: 'category', label: 'Category' },
  { key: 'payment_method', label: 'Payment method' },
  { key: 'notes', label: 'Notes' },
]
const MAX_BYTES = 10 * 1024 * 1024

/** Rows selected by default: valid and not flagged as duplicates. */
export function defaultSelection(batch: ImportBatchOut): Set<number> {
  return new Set(batch.rows.filter((r) => r.selected).map((r) => r.row))
}

export function ImportWizard() {
  const qc = useQueryClient()
  const accounts = useAccounts()
  const { money, date } = useFormatters()
  const [file, setFile] = useState<File | null>(null)
  const [accountId, setAccountId] = useState('')
  const [dateFormat, setDateFormat] = useState('DD/MM/YYYY')
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [headers, setHeaders] = useState<string[]>([])
  const [batch, setBatch] = useState<ImportBatchOut | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [undoOpen, setUndoOpen] = useState(false)

  const preview = async (withMapping: boolean) => {
    if (!file || !accountId) return
    if (file.size > MAX_BYTES) {
      setError('That file is larger than 10 MB.')
      return
    }
    setBusy(true)
    setError(null)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('account_id', accountId)
    fd.append('date_format', dateFormat)
    if (withMapping) {
      const clean = Object.fromEntries(Object.entries(mapping).filter(([, v]) => v))
      fd.append('column_mapping', JSON.stringify(clean))
    }
    try {
      const b = await api.post<ImportBatchOut>('/imports', fd)
      setBatch(b)
      setHeaders(b.headers)
      setMapping(b.column_mapping as Record<string, string>)
      setSelected(defaultSelection(b))
    } catch (err) {
      if (err instanceof ApiError && err.code === 'invalid_mapping') {
        const d = err.details[0] ?? {}
        setHeaders((d.headers as string[] | undefined) ?? [])
        setMapping((d.suggested as Record<string, string> | undefined) ?? {})
        setError('We could not detect the columns automatically. Map them below and preview again.')
      } else setError(errorMessage(err))
      setBatch(null)
    } finally {
      setBusy(false)
    }
  }

  const confirm = async () => {
    if (!batch) return
    setBusy(true)
    setError(null)
    try {
      const b = await api.post<ImportBatchOut>(`/imports/${batch.id}/confirm`, { selected_rows: [...selected].sort((a, z) => a - z) })
      setBatch(b)
      await invalidateFinancials(qc)
      toast.success(`Imported ${b.imported_count} transactions`)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const undo = async () => {
    if (!batch) return
    setBusy(true)
    try {
      const b = await api.post<ImportBatchOut>(`/imports/${batch.id}/undo`)
      setBatch(b)
      setUndoOpen(false)
      await invalidateFinancials(qc)
      toast.success('Import undone')
    } catch (err) {
      setError(errorMessage(err))
      setUndoOpen(false)
    } finally {
      setBusy(false)
    }
  }

  const toggle = (row: number) => {
    const next = new Set(selected)
    if (next.has(row)) next.delete(row)
    else next.add(row)
    setSelected(next)
  }

  const done = batch && batch.status !== 'preview'

  return (
    <div>
      <PageHeader title="Import transactions" description="Upload a CSV statement, check the preview, then import." />
      {error && <p role="alert" className="mb-4 rounded-md border border-destructive/40 bg-destructive/10 p-2 text-sm text-destructive">{error}</p>}
      {!done && (
        <Card className="mb-6">
          <CardHeader><CardTitle>1. Choose a file</CardTitle></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-3">
            <div className="grid gap-1.5">
              <Label htmlFor="imp-file">CSV file (max 10 MB, 5,000 rows)</Label>
              <input id="imp-file" type="file" accept=".csv,text/csv" className="text-sm"
                onChange={(e) => { setFile(e.target.files?.[0] ?? null); setBatch(null) }} />
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="imp-account">Import into account</Label>
              <NativeSelect id="imp-account" value={accountId} onChange={(e) => setAccountId(e.target.value)}>
                <option value="">Choose…</option>
                {(accounts.data ?? []).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </NativeSelect>
            </div>
            <div className="grid gap-1.5">
              <Label htmlFor="imp-date">Date format in the file</Label>
              <NativeSelect id="imp-date" value={dateFormat} onChange={(e) => setDateFormat(e.target.value)}>
                {DATE_FORMATS.map((f) => <option key={f} value={f}>{f}</option>)}
              </NativeSelect>
            </div>
            <div className="md:col-span-3">
              <Button disabled={!file || !accountId || busy} onClick={() => void preview(false)}>
                {busy && <Spinner />} Preview
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      {!done && headers.length > 0 && (
        <Card className="mb-6">
          <CardHeader><CardTitle>2. Column mapping</CardTitle></CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {MAPPING_FIELDS.map((f) => (
              <div key={f.key} className="grid gap-1">
                <Label htmlFor={`map-${f.key}`} className="text-xs">{f.label}</Label>
                <NativeSelect id={`map-${f.key}`} value={mapping[f.key] ?? ''}
                  onChange={(e) => setMapping({ ...mapping, [f.key]: e.target.value })}>
                  <option value="">Not in file</option>
                  {headers.map((h) => <option key={h} value={h}>{h}</option>)}
                </NativeSelect>
              </div>
            ))}
            <div className="sm:col-span-2 lg:col-span-5">
              <Button variant="secondary" disabled={busy} onClick={() => void preview(true)}>Preview with this mapping</Button>
            </div>
          </CardContent>
        </Card>
      )}
      {batch && batch.status === 'preview' && (
        <Card>
          <CardHeader>
            <CardTitle>3. Review and import</CardTitle>
            <p className="text-sm text-muted-foreground">
              {batch.row_count} rows · {batch.valid_count} valid · {batch.invalid_count} with errors · {batch.duplicate_count} possible duplicates.
              Rows with errors can't be imported; duplicates are unselected until you tick them.
            </p>
          </CardHeader>
          <CardContent>
            <div className="max-h-[60svh] overflow-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead><span className="sr-only">Import</span></TableHead>
                    <TableHead>Row</TableHead>
                    <TableHead>Date</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Category</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {batch.rows.map((r) => {
                    const invalid = r.errors.length > 0
                    return (
                      <TableRow key={r.row} data-state={invalid ? 'invalid' : r.duplicate ? 'duplicate' : 'ok'}>
                        <TableCell>
                          <input type="checkbox" className="accent-primary" disabled={invalid} checked={selected.has(r.row)}
                            onChange={() => toggle(r.row)} aria-label={`Import row ${r.row}`} />
                        </TableCell>
                        <TableCell>{r.row}</TableCell>
                        <TableCell className="whitespace-nowrap">{date(r.date)}</TableCell>
                        <TableCell className="max-w-56 truncate">{r.description ?? r.payee ?? '—'}</TableCell>
                        <TableCell>{r.type ?? '—'}</TableCell>
                        <TableCell>{r.category_name ?? '—'}</TableCell>
                        <TableCell className="text-right tabular-nums">{r.amount ? money(r.amount) : '—'}</TableCell>
                        <TableCell className="min-w-48 text-xs">
                          {invalid && <span className="text-destructive">{r.errors.join('; ')}</span>}
                          {!invalid && r.duplicate && <Badge variant="outline" className="border-warning text-warning">Possible duplicate</Badge>}
                          {r.warnings.map((w) => <p key={w} className="text-muted-foreground">{w}</p>)}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            </div>
            <div className="mt-4 flex items-center gap-3">
              <Button disabled={busy || selected.size === 0} onClick={() => void confirm()}>
                {busy && <Spinner />} Import {selected.size} selected row{selected.size === 1 ? '' : 's'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
      {done && batch && (
        <Card>
          <CardContent className="grid gap-3 p-6">
            {batch.status === 'confirmed' ? (
              <>
                <p className="font-medium">Imported {batch.imported_count} transactions from {batch.file_name}.</p>
                <div className="flex flex-wrap gap-2">
                  <Button asChild><Link to={`/transactions?import_batch_id=${batch.id}`}>View transactions</Link></Button>
                  {batch.undo_available_until && (
                    <Button variant="outline" onClick={() => setUndoOpen(true)}>Undo import</Button>
                  )}
                </div>
                {batch.undo_available_until && (
                  <p className="text-xs text-muted-foreground">You can undo this import until {new Date(batch.undo_available_until).toLocaleString('en-IN')}.</p>
                )}
              </>
            ) : (
              <p className="font-medium">This import was undone; its transactions were deleted.</p>
            )}
            <div><Button variant="ghost" onClick={() => { setBatch(null); setFile(null); setHeaders([]) }}>Import another file</Button></div>
          </CardContent>
        </Card>
      )}
      <ConfirmDialog open={undoOpen} onOpenChange={setUndoOpen} title="Undo this import?"
        description={batch ? `This deletes all ${batch.imported_count} transactions imported from ${batch.file_name}.` : undefined}
        confirmLabel="Undo import" pending={busy} onConfirm={() => void undo()} />
    </div>
  )
}
