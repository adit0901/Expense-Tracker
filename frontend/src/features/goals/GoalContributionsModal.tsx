import { Trash2 } from 'lucide-react'
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
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import type { GoalOut } from '@/services/api/types'

import { useDeleteContribution, useGoalContributions } from './api'

interface GoalContributionsModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  goal: GoalOut
}

export function GoalContributionsModal({
  open,
  onOpenChange,
  goal,
}: GoalContributionsModalProps) {
  const { money, date } = useFormatters()
  const contributionsQuery = useGoalContributions(goal.id)
  const deleteContribution = useDeleteContribution(goal.id)

  const items = contributionsQuery.data ?? []

  const handleDelete = async (cid: string) => {
    try {
      await deleteContribution.mutateAsync(cid)
      toast.success('Entry removed')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Contributions History: {goal.name}</DialogTitle>
          <DialogDescription>
            Audit log of all contributions and withdrawals towards this goal.
          </DialogDescription>
        </DialogHeader>

        <div className="py-2">
          {contributionsQuery.isPending ? (
            <LoadingBlock label="Loading entries..." />
          ) : items.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No manual contributions or withdrawals recorded yet.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Notes</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-xs text-muted-foreground">
                      {date(String(item.date))}
                    </TableCell>
                    <TableCell>
                      {item.kind === 'withdrawal' ? (
                        <Badge variant="destructive">Withdrawal</Badge>
                      ) : (
                        <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                          Contribution
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right font-medium tabular-nums">
                      {item.kind === 'withdrawal' ? '−' : '+'}
                      {money(String(item.amount))}
                    </TableCell>
                    <TableCell className="max-w-[150px] truncate text-xs text-muted-foreground">
                      {item.notes ?? '—'}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="size-7 text-muted-foreground hover:text-destructive"
                        aria-label="Delete entry"
                        onClick={() => handleDelete(item.id)}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

