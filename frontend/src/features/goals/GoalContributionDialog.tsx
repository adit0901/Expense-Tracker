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
import type { GoalOut } from '@/services/api/types'

import { useAddContribution } from './api'

interface GoalContributionDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  goal: GoalOut
}

export function GoalContributionDialog({
  open,
  onOpenChange,
  goal,
}: GoalContributionDialogProps) {
  const addContribution = useAddContribution(goal.id)

  const [kind, setKind] = useState<'contribution' | 'withdrawal'>('contribution')
  const [amount, setAmount] = useState('')
  const [dateVal, setDateVal] = useState(() => new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await addContribution.mutateAsync({
        kind,
        data: {
          kind,
          amount,
          date: dateVal,
          notes: notes.trim() || null,
        },
      })
      toast.success(
        kind === 'withdrawal'
          ? `Withdrew ₹${amount} from ${goal.name}`
          : `Contributed ₹${amount} to ${goal.name}`,
      )
      setAmount('')
      setNotes('')
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record entry'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Record Entry: {goal.name}</DialogTitle>
            <DialogDescription>
              Add a new contribution or withdraw funds from this goal.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label>Type</Label>
              <div className="grid grid-cols-2 gap-2">
                <Button
                  type="button"
                  variant={kind === 'contribution' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setKind('contribution')}
                >
                  Contribution
                </Button>
                <Button
                  type="button"
                  variant={kind === 'withdrawal' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setKind('withdrawal')}
                >
                  Withdrawal
                </Button>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="entry-amount">Amount (₹)</Label>
              <Input
                id="entry-amount"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="25000.00"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="entry-date">Date</Label>
              <Input
                id="entry-date"
                type="date"
                value={dateVal}
                onChange={(e) => setDateVal(e.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="entry-notes">Notes (Optional)</Label>
              <Input
                id="entry-notes"
                placeholder="e.g. Monthly SIP transfer"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={addContribution.isPending}>
              {addContribution.isPending ? 'Recording...' : 'Confirm'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
