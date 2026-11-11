import { zodResolver } from '@hookform/resolvers/zod'
import { useQueryClient } from '@tanstack/react-query'
import { Plus, X } from 'lucide-react'
import { useState } from 'react'
import { useFieldArray, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { NativeSelect } from '@/components/ui/native-select'
import { Textarea } from '@/components/ui/textarea'
import { useAccounts } from '@/features/accounts/api'
import { FormAlert } from '@/features/auth/AuthCard'
import { categoryOptions, useCategories } from '@/features/categories/api'
import { useFormatters } from '@/features/settings/usePreferences'
import { PAYMENT_METHOD_LABELS, TRANSACTION_TYPE_LABELS, todayIso } from '@/lib/format'
import { applyServerErrors } from '@/lib/forms'
import { invalidateFinancials } from '@/lib/queryKeys'
import { ApiError, api } from '@/services/api/client'
import type { DuplicateCheckOut, TransactionOut } from '@/services/api/types'

import { useIncomeSources } from './api'

const AMOUNT = /^\d{1,13}(\.\d{1,2})?$/
const amount = z.string().trim().regex(AMOUNT, 'Enter an amount greater than 0 with up to 2 decimals')
  .refine((v) => !/^0+(\.0+)?$/.test(v), 'Amount must be greater than 0')

const schema = z.object({
  type: z.enum(['expense', 'income', 'transfer', 'refund']),
  account_id: z.string().min(1, 'Choose an account'),
  counter_account_id: z.string(),
  category_id: z.string(),
  payment_method: z.string(),
  income_source_id: z.string(),
  amount,
  txn_date: z.string().min(1, 'Choose a date'),
  payee: z.string().max(120),
  description: z.string().max(255, 'Keep the description under 255 characters'),
  notes: z.string().max(2000),
  tags: z.string().max(400),
  has_breakdown: z.boolean(),
  gross: z.string(),
  deductions: z.array(z.object({ name: z.string().max(60), amount: z.string() })),
}).superRefine((v, ctx) => {
  if (v.type === 'transfer') {
    if (!v.counter_account_id) ctx.addIssue({ code: 'custom', path: ['counter_account_id'], message: 'Choose the destination account' })
    else if (v.counter_account_id === v.account_id) ctx.addIssue({ code: 'custom', path: ['counter_account_id'], message: 'Source and destination must differ' })
  } else if (!v.category_id) ctx.addIssue({ code: 'custom', path: ['category_id'], message: 'Choose a category' })
  if (v.type === 'expense' && !v.payment_method) ctx.addIssue({ code: 'custom', path: ['payment_method'], message: 'Choose a payment method' })
  if (v.type === 'income' && v.has_breakdown) {
    if (!AMOUNT.test(v.gross)) ctx.addIssue({ code: 'custom', path: ['gross'], message: 'Enter the gross salary' })
    v.deductions.forEach((d, i) => {
      if (!d.name.trim()) ctx.addIssue({ code: 'custom', path: ['deductions', i, 'name'], message: 'Name required' })
      if (!AMOUNT.test(d.amount)) ctx.addIssue({ code: 'custom', path: ['deductions', i, 'amount'], message: 'Amount required' })
    })
  }
})
export type TxnFormValues = z.infer<typeof schema>

const FIELDS = ['type', 'account_id', 'counter_account_id', 'category_id', 'payment_method', 'income_source_id',
  'amount', 'txn_date', 'payee', 'description', 'notes', 'tags'] as const

function toValues(t?: TransactionOut, defaults: Partial<TxnFormValues> = {}): TxnFormValues {
  return {
    type: t?.type ?? 'expense',
    account_id: t?.account_id ?? '',
    counter_account_id: t?.counter_account_id ?? '',
    category_id: t?.category_id ?? '',
    payment_method: t?.payment_method ?? '',
    income_source_id: t?.income_source_id ?? '',
    amount: t?.amount ?? '',
    txn_date: t?.txn_date ?? todayIso(),
    payee: t?.payee ?? '',
    description: t?.description ?? '',
    notes: t?.notes ?? '',
    tags: t?.tags.join(', ') ?? '',
    has_breakdown: !!t?.salary_breakdown,
    gross: t?.salary_breakdown?.gross ?? '',
    deductions: t?.salary_breakdown?.deductions.map((d) => ({ name: d.name, amount: d.amount })) ?? [],
    ...defaults,
  }
}

export function toPayload(v: TxnFormValues, confirmDuplicate = false): Record<string, unknown> {
  const isTransfer = v.type === 'transfer'
  const isIncome = v.type === 'income'
  return {
    type: v.type,
    account_id: v.account_id,
    counter_account_id: isTransfer ? v.counter_account_id : null,
    category_id: isTransfer ? null : v.category_id,
    payment_method: isIncome ? null : v.payment_method || null,
    income_source_id: isIncome && v.income_source_id ? v.income_source_id : null,
    amount: v.amount.trim(),
    txn_date: v.txn_date,
    payee: v.payee.trim() || null,
    description: v.description.trim() || null,
    notes: v.notes.trim() || null,
    tags: v.tags.split(',').map((t) => t.trim()).filter(Boolean),
    salary_breakdown: isIncome && v.has_breakdown
      ? { gross: v.gross.trim(), deductions: v.deductions.map((d) => ({ name: d.name.trim(), amount: d.amount.trim() })) }
      : null,
    confirm_duplicate: confirmDuplicate,
  }
}

export function TransactionFormDialog({ open, onOpenChange, transaction, defaults }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  transaction?: TransactionOut
  defaults?: Partial<TxnFormValues>
}) {
  // The form mounts with the dialog content, so its state resets each time it opens.
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{transaction ? 'Edit transaction' : 'Add transaction'}</DialogTitle>
          <DialogDescription>Amounts are always positive; the type sets the direction.</DialogDescription>
        </DialogHeader>
        <TransactionForm transaction={transaction} defaults={defaults} onClose={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  )
}

export function TransactionForm({ transaction, defaults, onClose }: {
  transaction?: TransactionOut
  defaults?: Partial<TxnFormValues>
  onClose: () => void
}) {
  const qc = useQueryClient()
  const { money, date } = useFormatters()
  const accounts = useAccounts()
  const cats = useCategories()
  const sources = useIncomeSources()
  const [formError, setFormError] = useState<string | null>(null)
  const [duplicates, setDuplicates] = useState<DuplicateCheckOut['candidates'] | null>(null)
  const form = useForm<TxnFormValues>({ resolver: zodResolver(schema), defaultValues: toValues(transaction, defaults) })
  const { register, handleSubmit, setError, formState, control } = form
  const deductions = useFieldArray({ control, name: 'deductions' })

  const type = useWatch({ control, name: 'type' })
  const hasBreakdown = useWatch({ control, name: 'has_breakdown' })
  const activeAccounts = (accounts.data ?? []).filter((a) => !a.archived_at || a.id === transaction?.account_id
    || a.id === transaction?.counter_account_id)
  const catKind = type === 'income' ? 'income' : 'expense'
  const catOpts = cats.data ? categoryOptions(cats.data, catKind) : []

  const submit = async (values: TxnFormValues, confirmDuplicate: boolean) => {
    setFormError(null)
    const body = toPayload(values, confirmDuplicate)
    try {
      if (transaction) await api.patch(`/transactions/${transaction.id}`, body)
      else await api.post('/transactions', body)
      await invalidateFinancials(qc)
      toast.success(transaction ? 'Transaction updated' : 'Transaction saved')
      onClose()
    } catch (err) {
      if (err instanceof ApiError && err.code === 'possible_duplicate') {
        setDuplicates(err.details.map((d) => d.candidate as DuplicateCheckOut['candidates'][number]))
        return
      }
      if (err instanceof ApiError && err.code === 'salary_breakdown_mismatch') {
        const expected = err.details[0]?.expected_net as string | undefined
        setError('gross', { type: 'server', message: expected
          ? `Gross minus deductions is ${money(expected)}, which doesn't match the amount credited.`
          : err.message })
        setFormError(err.message)
        return
      }
      setFormError(applyServerErrors(err, setError, FIELDS))
    }
  }

  const onSubmit = handleSubmit((v) => submit(v, false))
  const confirmDuplicate = handleSubmit((v) => submit(v, true))
  const e = formState.errors

  return (
        <form onSubmit={onSubmit} noValidate className="grid gap-4">
          <FormAlert message={formError} />
          {duplicates && (
            <div role="alert" className="rounded-md border border-warning/50 bg-warning/10 p-3 text-sm">
              <p className="font-medium">This looks like a possible duplicate of:</p>
              <ul className="mt-1 list-disc pl-5">
                {duplicates.map((d) => (
                  <li key={d.id}>{date(d.txn_date)} · {money(d.amount)} · {d.payee ?? d.description ?? 'No description'}</li>
                ))}
              </ul>
              <div className="mt-2 flex gap-2">
                <Button type="button" size="sm" onClick={() => void confirmDuplicate()}>Save anyway</Button>
                <Button type="button" size="sm" variant="outline" onClick={() => setDuplicates(null)}>Review</Button>
              </div>
            </div>
          )}
          <fieldset className="grid gap-2">
            <legend className="mb-1 text-sm font-medium">Type</legend>
            <div className="flex flex-wrap gap-3">
              {(['expense', 'income', 'transfer', 'refund'] as const).map((t) => (
                <label key={t} className="flex items-center gap-1.5 text-sm">
                  <input type="radio" value={t} {...register('type')} className="accent-primary" />
                  {TRANSACTION_TYPE_LABELS[t]}
                </label>
              ))}
            </div>
          </fieldset>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label={type === 'transfer' ? 'From account' : 'Account'} error={e.account_id?.message}>
              {(p) => (
                <NativeSelect {...p} {...register('account_id')}>
                  <option value="">Choose…</option>
                  {activeAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                </NativeSelect>
              )}
            </FormField>
            {type === 'transfer' ? (
              <FormField label="To account" hint="Paying a credit card bill? Choose the card here." error={e.counter_account_id?.message}>
                {(p) => (
                  <NativeSelect {...p} {...register('counter_account_id')}>
                    <option value="">Choose…</option>
                    {activeAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                  </NativeSelect>
                )}
              </FormField>
            ) : (
              <FormField label="Category" error={e.category_id?.message}>
                {(p) => (
                  <NativeSelect {...p} {...register('category_id')}>
                    <option value="">Choose…</option>
                    {catOpts.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </NativeSelect>
                )}
              </FormField>
            )}
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Amount (₹)" error={e.amount?.message}>
              {(p) => <Input inputMode="decimal" placeholder="0.00" {...p} {...register('amount')} />}
            </FormField>
            <FormField label="Date" error={e.txn_date?.message}>
              {(p) => <Input type="date" {...p} {...register('txn_date')} />}
            </FormField>
          </div>
          {type !== 'income' && (
            <FormField label={type === 'expense' ? 'Payment method' : 'Payment method (optional)'} error={e.payment_method?.message}>
              {(p) => (
                <NativeSelect {...p} {...register('payment_method')}>
                  <option value="">{type === 'expense' ? 'Choose…' : 'None'}</option>
                  {Object.entries(PAYMENT_METHOD_LABELS).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </NativeSelect>
              )}
            </FormField>
          )}
          {type === 'income' && (
            <FormField label="Income source (optional)" error={e.income_source_id?.message}>
              {(p) => (
                <NativeSelect {...p} {...register('income_source_id')}>
                  <option value="">None</option>
                  {(sources.data ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
                </NativeSelect>
              )}
            </FormField>
          )}
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label={type === 'income' ? 'Source / payer (optional)' : 'Payee (optional)'} error={e.payee?.message}>
              {(p) => <Input {...p} {...register('payee')} />}
            </FormField>
            <FormField label="Tags (comma separated)" error={e.tags?.message}>
              {(p) => <Input {...p} {...register('tags')} />}
            </FormField>
          </div>
          <FormField label="Description (optional)" error={e.description?.message}>
            {(p) => <Input maxLength={255} {...p} {...register('description')} />}
          </FormField>
          <FormField label="Notes (optional)" error={e.notes?.message}>
            {(p) => <Textarea rows={2} {...p} {...register('notes')} />}
          </FormField>
          {type === 'income' && (
            <fieldset className="grid gap-3 rounded-md border p-3">
              <legend className="px-1 text-sm font-medium">Salary breakdown</legend>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" {...register('has_breakdown')} className="accent-primary" />
                Record gross salary and deductions
              </label>
              {hasBreakdown && (
                <>
                  <p className="text-xs text-muted-foreground">
                    Gross minus deductions must equal the amount credited above. Deductions (TDS, EPF…) are not expenses.
                  </p>
                  <FormField label="Gross salary (₹)" error={e.gross?.message}>
                    {(p) => <Input inputMode="decimal" {...p} {...register('gross')} />}
                  </FormField>
                  {deductions.fields.map((f, i) => (
                    <div key={f.id} className="grid grid-cols-[1fr_8rem_auto] items-end gap-2">
                      <FormField label={`Deduction ${i + 1} name`} error={e.deductions?.[i]?.name?.message}>
                        {(p) => <Input placeholder="Income Tax/TDS" {...p} {...register(`deductions.${i}.name`)} />}
                      </FormField>
                      <FormField label="Amount" error={e.deductions?.[i]?.amount?.message}>
                        {(p) => <Input inputMode="decimal" {...p} {...register(`deductions.${i}.amount`)} />}
                      </FormField>
                      <Button type="button" variant="ghost" size="icon" aria-label={`Remove deduction ${i + 1}`} onClick={() => deductions.remove(i)}>
                        <X aria-hidden />
                      </Button>
                    </div>
                  ))}
                  <div>
                    <Button type="button" variant="outline" size="sm" onClick={() => deductions.append({ name: '', amount: '' })}>
                      <Plus aria-hidden /> Add deduction
                    </Button>
                  </div>
                </>
              )}
            </fieldset>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={formState.isSubmitting}>
              {formState.isSubmitting && <Spinner />} {transaction ? 'Save changes' : 'Save transaction'}
            </Button>
          </DialogFooter>
        </form>
  )
}
