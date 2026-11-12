import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { useAccounts } from '@/features/accounts/api'
import { useFormatters } from '@/features/settings/usePreferences'
import type { LoanOut } from '@/services/api/types'

import { useRecordPayment } from './api'

interface PrepaymentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  loan: LoanOut
}

export function PrepaymentDialog({ open, onOpenChange, loan }: PrepaymentDialogProps) {
  const { money } = useFormatters()
  const accountsQuery = useAccounts()
  const recordPayment = useRecordPayment(loan.id)

  const accounts = (accountsQuery.data ?? []).filter((a) => !a.archived_at)

  const [amount, setAmount] = useState('')
  const [accountId, setAccountId] = useState(accounts[0]?.id ?? '')
  const [paymentDate, setPaymentDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [strategy, setStrategy] = useState<'reduce_tenure' | 'reduce_emi'>('reduce_tenure')

  const handlePrepay = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!accountId) {
      toast.error('Please select an account')
      return
    }

    try {
      await recordPayment.mutateAsync({
        account_id: accountId,
        payment_date: paymentDate,
        payment_type: 'prepayment',
        amount,
        strategy,
      })
      toast.success(`Prepayment of ${money(amount)} recorded`)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record prepayment'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handlePrepay}>
          <DialogHeader>
            <DialogTitle>Make Loan Prepayment: {loan.lender}</DialogTitle>
            <DialogDescription>
              Prepayments reduce your outstanding principal directly and do not count as an expense.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="rounded-lg border bg-muted/30 p-2.5 text-xs">
              <span className="text-muted-foreground">Current Outstanding:</span>{' '}
              <strong className="text-foreground tabular-nums">
                {money(String(loan.current_outstanding))}
              </strong>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="prepay-amount">Prepayment Amount (₹)</Label>
              <Input
                id="prepay-amount"
                type="number"
                step="0.01"
                min="1"
                placeholder="500000.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="prepay-account">Source Account</Label>
              <select
                id="prepay-account"
                aria-label="Source account"
                className="h-9 w-full rounded-md border bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={accountId}
                onChange={(e) => setAccountId(e.target.value)}
                required
              >
                {accounts.length === 0 && <option value="">No active accounts found</option>}
                {accounts.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.name} ({a.type})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="prepay-date">Payment Date</Label>
              <Input
                id="prepay-date"
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label>Prepayment Strategy</Label>
              <RadioGroup
                value={strategy}
                onValueChange={(val) => setStrategy(val as 'reduce_tenure' | 'reduce_emi')}
                className="space-y-2"
              >
                <div className="flex items-start space-x-2 rounded-md border p-2.5">
                  <RadioGroupItem value="reduce_tenure" id="st-tenure" className="mt-0.5" />
                  <div className="space-y-0.5 text-xs">
                    <Label htmlFor="st-tenure" className="font-medium cursor-pointer">
                      Reduce Tenure (Keep EMI)
                    </Label>
                    <p className="text-muted-foreground">
                      Maintains your current monthly EMI and repays the loan sooner, saving maximum interest.
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-2 rounded-md border p-2.5">
                  <RadioGroupItem value="reduce_emi" id="st-emi" className="mt-0.5" />
                  <div className="space-y-0.5 text-xs">
                    <Label htmlFor="st-emi" className="font-medium cursor-pointer">
                      Reduce EMI (Keep Tenure)
                    </Label>
                    <p className="text-muted-foreground">
                      Keeps the remaining months the same and lowers your monthly cash outflow.
                    </p>
                  </div>
                </div>
              </RadioGroup>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={recordPayment.isPending || !accountId}>
              {recordPayment.isPending ? 'Processing...' : 'Confirm Prepayment'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

