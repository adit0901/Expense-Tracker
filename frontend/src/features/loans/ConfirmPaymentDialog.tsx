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
import { useAccounts } from '@/features/accounts/api'
import { useFormatters } from '@/features/settings/usePreferences'
import type { InstallmentOut, LoanOut } from '@/services/api/types'

import { useRecordPayment } from './api'

interface ConfirmPaymentDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  loan: LoanOut
  installment?: InstallmentOut | null
}

export function ConfirmPaymentDialog({
  open,
  onOpenChange,
  loan,
  installment,
}: ConfirmPaymentDialogProps) {
  const { money } = useFormatters()
  const accountsQuery = useAccounts()
  const recordPayment = useRecordPayment(loan.id)

  const accounts = (accountsQuery.data ?? []).filter((a) => !a.archived_at)

  const [accountId, setAccountId] = useState(accounts[0]?.id ?? '')
  const [paymentDate, setPaymentDate] = useState(() =>
    installment ? String(installment.due_date) : new Date().toISOString().slice(0, 10),
  )

  const totalAmount = installment ? String(installment.payment) : String(loan.emi_amount)
  const principalComponent = installment ? String(installment.principal) : null
  const interestComponent = installment ? String(installment.interest) : null

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!accountId) {
      toast.error('Please select an account')
      return
    }

    try {
      await recordPayment.mutateAsync({
        account_id: accountId,
        payment_date: paymentDate,
        payment_type: 'installment',
        installment_no: installment?.installment_no,
      })
      toast.success(`EMI payment of ${money(totalAmount)} recorded`)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record payment'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleConfirm}>
          <DialogHeader>
            <DialogTitle>Confirm EMI Payment: {loan.lender}</DialogTitle>
            <DialogDescription>
              Confirm installment {installment ? `#${installment.installment_no}` : ''} payment.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Split Breakdown Card */}
            <div className="rounded-lg border bg-muted/40 p-3 space-y-2">
              <div className="flex justify-between text-sm font-semibold">
                <span>Total Payment:</span>
                <span className="tabular-nums text-primary">{money(totalAmount)}</span>
              </div>

              {principalComponent && interestComponent && (
                <div className="border-t pt-2 space-y-1 text-xs">
                  <div className="flex justify-between text-muted-foreground">
                    <span>Principal Component (Reduces Liability):</span>
                    <span className="font-medium tabular-nums text-foreground">
                      {money(principalComponent)}
                    </span>
                  </div>
                  <div className="flex justify-between text-muted-foreground">
                    <span>Interest Component (Expense):</span>
                    <span className="font-medium tabular-nums text-destructive">
                      {money(interestComponent)}
                    </span>
                  </div>
                </div>
              )}
              <p className="text-[11px] text-muted-foreground italic pt-1">
                Note: In line with accounting standards, only the interest portion will increase your expenses. The principal portion reduces your outstanding loan liability.
              </p>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="pay-account">Source Account</Label>
              <select
                id="pay-account"
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
              <Label htmlFor="pay-date">Payment Date</Label>
              <Input
                id="pay-date"
                type="date"
                value={paymentDate}
                onChange={(e) => setPaymentDate(e.target.value)}
                required
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={recordPayment.isPending || !accountId}>
              {recordPayment.isPending ? 'Confirming...' : 'Confirm EMI Payment'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

