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

import { useCopyBudget } from './api'

interface CopyForwardDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  currentMonth: string
}

function getPreviousMonth(month: string): string {
  const [y, m] = month.split('-').map(Number)
  if (!y || !m) return month
  const prevDate = new Date(Date.UTC(y, m - 2, 1))
  const py = prevDate.getUTCFullYear()
  const pm = String(prevDate.getUTCMonth() + 1).padStart(2, '0')
  return `${py}-${pm}`
}

export function CopyForwardDialog({
  open,
  onOpenChange,
  currentMonth,
}: CopyForwardDialogProps) {
  const [sourceMonth, setSourceMonth] = useState(() => getPreviousMonth(currentMonth))
  const copyBudget = useCopyBudget(currentMonth)

  const handleCopy = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!sourceMonth) return
    try {
      await copyBudget.mutateAsync(sourceMonth)
      toast.success(`Copied budgets from ${sourceMonth} to ${currentMonth}`)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to copy budgets'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleCopy}>
          <DialogHeader>
            <DialogTitle>Copy Budgets Forward</DialogTitle>
            <DialogDescription>
              Copy all category and overall budgets from a previous month into {currentMonth}.
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <Label htmlFor="source-month">Source Month</Label>
            <Input
              id="source-month"
              type="month"
              className="mt-1.5"
              value={sourceMonth}
              onChange={(e) => setSourceMonth(e.target.value)}
              required
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={copyBudget.isPending}>
              {copyBudget.isPending ? 'Copying...' : 'Copy Budgets'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

