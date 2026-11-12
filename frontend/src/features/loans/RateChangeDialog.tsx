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
import type { LoanOut } from '@/services/api/types'

import { useAddLoanEvent } from './api'

interface RateChangeDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  loan: LoanOut
}

export function RateChangeDialog({ open, onOpenChange, loan }: RateChangeDialogProps) {
  const addEvent = useAddLoanEvent(loan.id)

  const [annualRate, setAnnualRate] = useState('')
  const [effectiveDate, setEffectiveDate] = useState(() =>
    new Date().toISOString().slice(0, 10),
  )
  const [strategy, setStrategy] = useState<'keep_emi' | 'keep_tenure'>('keep_emi')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await addEvent.mutateAsync({
        kind: 'rate_change',
        effective_date: effectiveDate,
        payload: {
          annual_rate: annualRate,
          strategy,
        },
      })
      toast.success('Interest rate change recorded')
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record rate change'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Record Interest Rate Change: {loan.lender}</DialogTitle>
            <DialogDescription>
              Update the interest rate on this floating-rate loan and adjust tenure or EMI.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="rounded-lg border bg-muted/30 p-2.5 text-xs">
              <span className="text-muted-foreground">Current Rate:</span>{' '}
              <strong className="text-foreground">{loan.annual_rate}% p.a.</strong>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="new-rate">New Annual Interest Rate (%)</Label>
              <Input
                id="new-rate"
                type="number"
                step="0.01"
                min="0"
                placeholder="9.00"
                value={annualRate}
                onChange={(e) => setAnnualRate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="effective-date">Effective Date</Label>
              <Input
                id="effective-date"
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                required
              />
            </div>

            <div className="space-y-2">
              <Label>Adjustment Strategy</Label>
              <RadioGroup
                value={strategy}
                onValueChange={(val) => setStrategy(val as 'keep_emi' | 'keep_tenure')}
                className="space-y-2"
              >
                <div className="flex items-start space-x-2 rounded-md border p-2.5">
                  <RadioGroupItem value="keep_emi" id="rc-emi" className="mt-0.5" />
                  <div className="space-y-0.5 text-xs">
                    <Label htmlFor="rc-emi" className="font-medium cursor-pointer">
                      Keep EMI (Adjust Tenure)
                    </Label>
                    <p className="text-muted-foreground">
                      Maintains your current monthly payment and extends or shortens the remaining months.
                    </p>
                  </div>
                </div>

                <div className="flex items-start space-x-2 rounded-md border p-2.5">
                  <RadioGroupItem value="keep_tenure" id="rc-tenure" className="mt-0.5" />
                  <div className="space-y-0.5 text-xs">
                    <Label htmlFor="rc-tenure" className="font-medium cursor-pointer">
                      Keep Tenure (Adjust EMI)
                    </Label>
                    <p className="text-muted-foreground">
                      Keeps the planned end date unchanged and recalculates your monthly installment.
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
            <Button type="submit" disabled={addEvent.isPending}>
              {addEvent.isPending ? 'Updating...' : 'Apply Rate Change'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

