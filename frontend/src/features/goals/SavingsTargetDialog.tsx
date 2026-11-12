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

import { useSetSavingsTarget } from './api'

interface SavingsTargetDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentMonth: string
  currentTargetAmount?: string | number
}

export function SavingsTargetDialog({
  open,
  onOpenChange,
  currentMonth,
  currentTargetAmount,
}: SavingsTargetDialogProps) {
  const setTarget = useSetSavingsTarget()
  const [effectiveFrom, setEffectiveFrom] = useState(currentMonth)
  const [amount, setAmount] = useState(() => (currentTargetAmount ? String(currentTargetAmount) : ''))

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await setTarget.mutateAsync({
        effectiveFrom,
        data: { amount: parseFloat(amount || '0').toFixed(2) },
      })
      toast.success(`Savings target set to ₹${amount} from ${effectiveFrom}`)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to set target'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSave}>
          <DialogHeader>
            <DialogTitle>Set Monthly Savings Target</DialogTitle>
            <DialogDescription>
              Set your desired monthly savings goal. This target will stay active from the chosen month onward until changed.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="target-effective-from">Effective From Month</Label>
              <Input
                id="target-effective-from"
                type="month"
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="target-amount-input">Target Amount (₹ / month)</Label>
              <Input
                id="target-amount-input"
                type="number"
                step="0.01"
                min="1"
                placeholder="30000.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={setTarget.isPending}>
              {setTarget.isPending ? 'Saving...' : 'Save Target'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

