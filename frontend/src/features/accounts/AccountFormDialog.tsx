import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { FormField } from '@/components/common/FormField'
import { Spinner } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { FormAlert } from '@/features/auth/AuthCard'
import { ACCOUNT_TYPE_LABELS, todayIso } from '@/lib/format'
import { applyServerErrors } from '@/lib/forms'
import { invalidateFinancials } from '@/lib/queryKeys'
import { api } from '@/services/api/client'
import type { AccountOut } from '@/services/api/types'

export const AMOUNT_RE = /^-?\d{1,13}(\.\d{1,2})?$/

const schema = z.object({
  name: z.string().trim().min(1, 'Enter a name').max(100),
  type: z.enum(['bank', 'cash', 'credit_card', 'wallet']),
  institution: z.string().trim().max(100),
  last4: z.string().trim().regex(/^(\d{4})?$/, 'Enter exactly the last 4 digits (never the full number)'),
  opening_balance: z.string().trim().regex(AMOUNT_RE, 'Enter an amount with up to 2 decimals'),
  opening_date: z.string().min(1, 'Choose a date'),
})
type Values = z.infer<typeof schema>
const FIELDS = ['name', 'type', 'institution', 'last4', 'opening_balance', 'opening_date'] as const

export function AccountFormDialog({ open, onOpenChange, account }: {
  open: boolean
  onOpenChange: (open: boolean) => void
  account?: AccountOut
}) {
  const qc = useQueryClient()
  const [formError, setFormError] = useState<string | null>(null)
  const { register, handleSubmit, setError, formState, control } = useForm<Values>({
    resolver: zodResolver(schema),
    values: {
      name: account?.name ?? '',
      type: account?.type ?? 'bank',
      institution: account?.institution ?? '',
      last4: account?.last4 ?? '',
      opening_balance: account?.opening_balance ?? '0.00',
      opening_date: account?.opening_date ?? todayIso(),
    },
  })
  const mutation = useMutation({
    mutationFn: (v: Values) => {
      const body = { ...v, institution: v.institution || null, last4: v.last4 || null }
      return account ? api.patch<AccountOut>(`/accounts/${account.id}`, body) : api.post<AccountOut>('/accounts', body)
    },
  })
  const isCard = useWatch({ control, name: 'type' }) === 'credit_card'

  const onSubmit = handleSubmit(async (v) => {
    setFormError(null)
    try {
      await mutation.mutateAsync(v)
      await invalidateFinancials(qc)
      toast.success(account ? 'Account updated' : 'Account created')
      onOpenChange(false)
    } catch (err) {
      setFormError(applyServerErrors(err, setError, FIELDS))
    }
  })

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{account ? 'Edit account' : 'Add account'}</DialogTitle>
        </DialogHeader>
        <form onSubmit={onSubmit} noValidate className="grid gap-4">
          <FormAlert message={formError} />
          <FormField label="Name" error={formState.errors.name?.message}>
            {(p) => <Input placeholder="HDFC Savings" {...p} {...register('name')} />}
          </FormField>
          <FormField label="Type" error={formState.errors.type?.message}>
            {(p) => (
              <Controller control={control} name="type" render={({ field }) => (
                <Select value={field.value} onValueChange={field.onChange}>
                  <SelectTrigger className="w-full" {...p}><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(ACCOUNT_TYPE_LABELS).map(([v, l]) => (
                      <SelectItem key={v} value={v}>{l}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )} />
            )}
          </FormField>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label="Institution (optional)" error={formState.errors.institution?.message}>
              {(p) => <Input {...p} {...register('institution')} />}
            </FormField>
            <FormField label="Last 4 digits (optional)" error={formState.errors.last4?.message}>
              {(p) => <Input inputMode="numeric" maxLength={20} {...p} {...register('last4')} />}
            </FormField>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <FormField label={isCard ? 'Opening outstanding (₹)' : 'Opening balance (₹)'} error={formState.errors.opening_balance?.message}>
              {(p) => <Input inputMode="decimal" {...p} {...register('opening_balance')} />}
            </FormField>
            <FormField label="Opening date" error={formState.errors.opening_date?.message}>
              {(p) => <Input type="date" {...p} {...register('opening_date')} />}
            </FormField>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={formState.isSubmitting}>
              {formState.isSubmitting && <Spinner />} {account ? 'Save changes' : 'Add account'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
