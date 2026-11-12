import { useEffect, useState } from 'react'
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
import type { GoalCreate, GoalOut, GoalType } from '@/services/api/types'

import { useCreateGoal, useUpdateGoal } from './api'

interface GoalFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  goal?: GoalOut | null
}

const GOAL_TYPES: { value: GoalType; label: string }[] = [
  { value: 'emergency_fund', label: 'Emergency Fund' },
  { value: 'vacation', label: 'Vacation' },
  { value: 'house', label: 'House / Real Estate' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'education', label: 'Education' },
  { value: 'retirement', label: 'Retirement' },
  { value: 'other', label: 'Other Goal' },
]

export function GoalFormDialog({ open, onOpenChange, goal }: GoalFormDialogProps) {
  const createGoal = useCreateGoal()
  const updateGoal = useUpdateGoal(goal?.id ?? '')

  const [name, setName] = useState('')
  const [type, setType] = useState<GoalType>('emergency_fund')
  const [targetAmount, setTargetAmount] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [startingAmount, setStartingAmount] = useState('0.00')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    if (open) {
      if (goal) {
        setName(goal.name)
        setType(goal.type)
        setTargetAmount(String(goal.target_amount))
        setTargetDate(goal.target_date ? goal.target_date.slice(0, 10) : '')
        setStartingAmount(String(goal.starting_amount ?? '0.00'))
        setNotes(goal.notes ?? '')
      } else {
        setName('')
        setType('emergency_fund')
        setTargetAmount('')
        setTargetDate('')
        setStartingAmount('0.00')
        setNotes('')
      }
    }
  }, [open, goal])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      if (goal) {
        await updateGoal.mutateAsync({
          name: name.trim(),
          type,
          target_amount: targetAmount,
          target_date: targetDate || null,
          notes: notes.trim() || null,
        })
        toast.success('Goal updated')
      } else {
        const payload: GoalCreate = {
          name: name.trim(),
          type,
          target_amount: targetAmount,
          target_date: targetDate || null,
          starting_amount: startingAmount || '0.00',
          notes: notes.trim() || null,
        }
        await createGoal.mutateAsync(payload)
        toast.success('Goal created')
      }
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save goal'
      toast.error(msg)
    }
  }

  const isSaving = createGoal.isPending || updateGoal.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>{goal ? 'Edit Goal' : 'Create Financial Goal'}</DialogTitle>
            <DialogDescription>
              Set up a target amount and deadline to track your progress over time.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="goal-name">Goal Name</Label>
              <Input
                id="goal-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Dream House Down Payment"
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="goal-type">Category / Type</Label>
              <select
                id="goal-type"
                className="h-9 w-full rounded-md border bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={type}
                onChange={(e) => setType(e.target.value as GoalType)}
              >
                {GOAL_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="goal-target-amount">Target Amount (₹)</Label>
                <Input
                  id="goal-target-amount"
                  type="number"
                  step="0.01"
                  min="1"
                  value={targetAmount}
                  onChange={(e) => setTargetAmount(e.target.value)}
                  placeholder="300000.00"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="goal-target-date">Target Date (Optional)</Label>
                <Input
                  id="goal-target-date"
                  type="date"
                  value={targetDate}
                  onChange={(e) => setTargetDate(e.target.value)}
                />
              </div>
            </div>

            {!goal && (
              <div className="space-y-1.5">
                <Label htmlFor="goal-starting-amount">Starting Amount (₹)</Label>
                <Input
                  id="goal-starting-amount"
                  type="number"
                  step="0.01"
                  min="0"
                  value={startingAmount}
                  onChange={(e) => setStartingAmount(e.target.value)}
                  placeholder="0.00"
                />
                <p className="text-xs text-muted-foreground">
                  Any existing funds already allocated to this goal.
                </p>
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="goal-notes">Notes (Optional)</Label>
              <Input
                id="goal-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Additional details..."
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? 'Saving...' : goal ? 'Update Goal' : 'Create Goal'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

