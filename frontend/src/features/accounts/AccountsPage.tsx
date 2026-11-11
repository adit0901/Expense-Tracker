import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Archive, Pencil, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { EmptyState, ErrorState, LoadingBlock, errorMessage } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { useFormatters } from '@/features/settings/usePreferences'
import { ACCOUNT_TYPE_LABELS } from '@/lib/format'
import { invalidateFinancials } from '@/lib/queryKeys'
import { ApiError, api } from '@/services/api/client'
import type { AccountOut } from '@/services/api/types'

import { AccountFormDialog } from './AccountFormDialog'
import { useAccounts, useAccountsSummary } from './api'

export function AccountsPage() {
  const [showArchived, setShowArchived] = useState(false)
  const accounts = useAccounts({ includeArchived: showArchived })
  const summary = useAccountsSummary()
  const { money } = useFormatters()
  const qc = useQueryClient()
  const [editing, setEditing] = useState<AccountOut | undefined>()
  const [formOpen, setFormOpen] = useState(false)
  const [archiving, setArchiving] = useState<AccountOut | null>(null)
  const [deleting, setDeleting] = useState<AccountOut | null>(null)

  const archive = useMutation({
    mutationFn: (a: AccountOut) => api.post(`/accounts/${a.id}/archive`),
    onSuccess: async () => {
      await invalidateFinancials(qc)
      toast.success('Account archived')
      setArchiving(null)
    },
    onError: (err) => toast.error(errorMessage(err)),
  })
  const remove = useMutation({
    mutationFn: (a: AccountOut) => api.del(`/accounts/${a.id}`),
    onSuccess: async () => {
      await invalidateFinancials(qc)
      toast.success('Account deleted')
      setDeleting(null)
    },
    onError: (err, a) => {
      setDeleting(null)
      if (err instanceof ApiError && err.code === 'account_has_transactions') {
        toast.error(err.message)
        setArchiving(a)
      } else toast.error(errorMessage(err))
    },
  })

  return (
    <div className="space-y-6">
      {summary.data && (
        <div className="grid gap-3 sm:grid-cols-3">
          <Card><CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Liquid funds (bank + cash)</p>
            <p className="text-xl font-semibold">{money(summary.data.liquid_funds)}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Wallets</p>
            <p className="text-xl font-semibold">{money(summary.data.wallet_balance)}</p>
          </CardContent></Card>
          <Card><CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Credit card outstanding</p>
            <p className="text-xl font-semibold">{money(summary.data.credit_card_outstanding)}</p>
          </CardContent></Card>
        </div>
      )}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Switch id="show-archived" checked={showArchived} onCheckedChange={setShowArchived} />
          <Label htmlFor="show-archived">Show archived</Label>
        </div>
        <Button onClick={() => { setEditing(undefined); setFormOpen(true) }}>
          <Plus aria-hidden /> Add account
        </Button>
      </div>
      {accounts.isPending ? (
        <LoadingBlock label="Loading accounts" />
      ) : accounts.isError ? (
        <ErrorState error={accounts.error} onRetry={() => void accounts.refetch()} />
      ) : accounts.data.length === 0 ? (
        <EmptyState title="No accounts yet" description="Add the bank accounts, cash, cards and wallets you use."
          action={<Button onClick={() => { setEditing(undefined); setFormOpen(true) }}>Add account</Button>} />
      ) : (
        <ul className="grid gap-3 md:grid-cols-2">
          {accounts.data.map((a) => (
            <li key={a.id}>
              <Card>
                <CardContent className="flex items-start justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{a.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {ACCOUNT_TYPE_LABELS[a.type]}{a.institution ? ` · ${a.institution}` : ''}{a.last4 ? ` · ••${a.last4}` : ''}
                    </p>
                    {a.archived_at && <Badge variant="secondary" className="mt-1">Archived</Badge>}
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">{a.balance_label}</p>
                    <p className="font-semibold tabular-nums">{money(a.current_balance)}</p>
                    <div className="mt-2 flex justify-end gap-1">
                      <Button variant="ghost" size="icon-sm" aria-label={`Edit ${a.name}`} onClick={() => { setEditing(a); setFormOpen(true) }}>
                        <Pencil aria-hidden />
                      </Button>
                      {!a.archived_at && (
                        <Button variant="ghost" size="icon-sm" aria-label={`Archive ${a.name}`} onClick={() => setArchiving(a)}>
                          <Archive aria-hidden />
                        </Button>
                      )}
                      <Button variant="ghost" size="icon-sm" aria-label={`Delete ${a.name}`} onClick={() => setDeleting(a)}>
                        <Trash2 aria-hidden />
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
      <AccountFormDialog open={formOpen} onOpenChange={setFormOpen} account={editing} />
      <ConfirmDialog
        open={!!archiving}
        onOpenChange={(o) => !o && setArchiving(null)}
        title={`Archive ${archiving?.name ?? 'account'}?`}
        description="Archived accounts are hidden from entry forms but their history stays in reports."
        confirmLabel="Archive"
        pending={archive.isPending}
        onConfirm={() => archiving && archive.mutate(archiving)}
      />
      <ConfirmDialog
        open={!!deleting}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={`Delete ${deleting?.name ?? 'account'}?`}
        description="Accounts with transactions can't be deleted; you'll be offered archiving instead."
        pending={remove.isPending}
        onConfirm={() => deleting && remove.mutate(deleting)}
      />
    </div>
  )
}
