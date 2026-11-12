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
import type { LiabilityCreate } from '@/services/api/types'

import { useCreateLiability } from './api'

interface LiabilityFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function LiabilityFormDialog({ open, onOpenChange }: LiabilityFormDialogProps) {
  const createLiability = useCreateLiability()

  const [name, setName] = useState('')
  const [initialBalance, setInitialBalance] = useState('')
  const [asOf, setAsOf] = useState(() => new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload: LiabilityCreate = {
        name: name.trim(),
        current_balance: initialBalance,
        as_of: asOf,
        notes: notes.trim() || null,
      }
      await createLiability.mutateAsync(payload)
      toast.success('Liability added')
      setName('')
      setInitialBalance('')
      setNotes('')
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add liability'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Other Liability</DialogTitle>
            <DialogDescription>
              Record non-bank liabilities such as informal debts or personal loans from family.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="liability-name">Liability Name</Label>
              <Input
                id="liability-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Loan from Uncle"
                required
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="liability-balance">Outstanding Balance (₹)</Label>
                <Input
                  id="liability-balance"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="80000.00"
                  value={initialBalance}
                  onChange={(e) => setInitialBalance(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="liability-as-of">As of Date</Label>
                <Input
                  id="liability-as-of"
                  type="date"
                  value={asOf}
                  onChange={(e) => setAsOf(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="liability-notes">Notes (Optional)</Label>
              <Input
                id="liability-notes"
                placeholder="Repayment terms or notes..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createLiability.isPending}>
              {createLiability.isPending ? 'Adding...' : 'Add Liability'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
