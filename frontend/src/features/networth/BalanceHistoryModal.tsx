import { Plus } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { LoadingBlock } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import type { LiabilityOut } from '@/services/api/types'

import { useAddLiabilityBalance, useCloseLiability, useLiabilityBalances } from './api'

interface BalanceHistoryModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  liability: LiabilityOut
}

export function BalanceHistoryModal({
  open,
  onOpenChange,
  liability,
}: BalanceHistoryModalProps) {
  const { money, date } = useFormatters()
  const balancesQuery = useLiabilityBalances(liability.id)
  const addBalance = useAddLiabilityBalance(liability.id)
  const closeLiability = useCloseLiability(liability.id)

  const [newBalance, setNewBalance] = useState('')
  const [newDate, setNewDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [closingDate, setClosingDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [showCloseForm, setShowCloseForm] = useState(false)

  const balances = balancesQuery.data ?? []

  const handleAddBalance = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await addBalance.mutateAsync({
        balance: newBalance,
        as_of: newDate,
      })
      toast.success('Balance updated')
      setNewBalance('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record balance'
      toast.error(msg)
    }
  }

  const handleCloseLiability = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await closeLiability.mutateAsync({
        closed_at: closingDate,
      })
      toast.success('Liability closed')
      setShowCloseForm(false)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to close liability'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Balance History: {liability.name}</DialogTitle>
            {liability.closed_at ? (
              <Badge variant="secondary">Closed</Badge>
            ) : (
              <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                Active
              </Badge>
            )}
          </div>
          <DialogDescription>
            Historical balances tracked across repayments over time.
          </DialogDescription>
        </DialogHeader>

        {!liability.closed_at && (
          <div className="rounded-lg border bg-muted/20 p-3 space-y-3">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground">
              Update Outstanding Balance
            </h4>
            <form onSubmit={handleAddBalance} className="flex items-end gap-2">
              <div className="flex-1 space-y-1">
                <Label htmlFor="bal-date" className="text-xs">
                  Date
                </Label>
                <Input
                  id="bal-date"
                  type="date"
                  className="h-8 text-xs"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  required
                />
              </div>
              <div className="flex-1 space-y-1">
                <Label htmlFor="bal-amt" className="text-xs">
                  Balance (₹)
                </Label>
                <Input
                  id="bal-amt"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="60000.00"
                  className="h-8 text-xs"
                  value={newBalance}
                  onChange={(e) => setNewBalance(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" size="sm" className="h-8 text-xs" disabled={addBalance.isPending}>
                <Plus className="mr-1 size-3" />
                Update
              </Button>
            </form>
          </div>
        )}

        <div className="py-2">
          {balancesQuery.isPending ? (
            <LoadingBlock label="Loading balance history..." />
          ) : balances.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No balance records.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>As of Date</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead className="text-right">Recorded At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {balances.map((b) => (
                  <TableRow key={b.id}>
                    <TableCell className="font-medium">{date(String(b.as_of))}</TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {money(String(b.balance))}
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {date(String(b.created_at))}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {!liability.closed_at && (
          <div className="border-t pt-3">
            {!showCloseForm ? (
              <Button
                variant="outline"
                size="sm"
                className="text-xs text-destructive hover:bg-destructive/10"
                onClick={() => setShowCloseForm(true)}
              >
                Close Liability (Settled / Forgiven)
              </Button>
            ) : (
              <form onSubmit={handleCloseLiability} className="space-y-3 rounded-lg border border-destructive/20 bg-destructive/5 p-3">
                <p className="text-xs text-muted-foreground">
                  Closing keeps past history for net worth snapshots but excludes this liability going forward.
                </p>
                <div className="flex items-end gap-2">
                  <div className="flex-1 space-y-1">
                    <Label htmlFor="close-bal-date" className="text-xs">
                      Closing Date
                    </Label>
                    <Input
                      id="close-bal-date"
                      type="date"
                      className="h-8 text-xs"
                      value={closingDate}
                      onChange={(e) => setClosingDate(e.target.value)}
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    variant="destructive"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={closeLiability.isPending}
                  >
                    Confirm Close
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => setShowCloseForm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

