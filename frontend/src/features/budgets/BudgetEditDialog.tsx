import { Plus, Trash2 } from 'lucide-react'
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
import { categoryOptions, useCategories } from '@/features/categories/api'
import type { BudgetLineInput, BudgetResponse } from '@/services/api/types'

import { useSetBudget } from './api'

interface BudgetEditDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  month: string
  currentBudget?: BudgetResponse
}

export function BudgetEditDialog({
  open,
  onOpenChange,
  month,
  currentBudget,
}: BudgetEditDialogProps) {
  const categoriesQuery = useCategories()
  const setBudget = useSetBudget(month)

  const [overallAmount, setOverallAmount] = useState('')
  const [lines, setLines] = useState<BudgetLineInput[]>([])

  useEffect(() => {
    if (open) {
      setOverallAmount(currentBudget?.overall_amount ?? '')
      if (currentBudget?.lines && currentBudget.lines.length > 0) {
        setLines(
          currentBudget.lines.map((l) => ({
            category_id: l.category_id,
            amount: l.amount,
            alert_thresholds: l.alert_thresholds ?? [80, 100],
          })),
        )
      } else {
        setLines([])
      }
    }
  }, [open, currentBudget])

  const expenseCategories = categoryOptions(categoriesQuery.data ?? [], 'expense')

  const handleAddLine = () => {
    const unused = expenseCategories.find(
      (c) => !lines.some((l) => l.category_id === c.value),
    )
    if (unused) {
      setLines([...lines, { category_id: unused.value, amount: '1000.00', alert_thresholds: [80, 100] }])
    } else if (expenseCategories.length > 0) {
      setLines([...lines, { category_id: expenseCategories[0]!.value, amount: '1000.00', alert_thresholds: [80, 100] }])
    }
  }

  const handleRemoveLine = (index: number) => {
    setLines(lines.filter((_, i) => i !== index))
  }

  const handleLineChange = (index: number, updates: Partial<BudgetLineInput>) => {
    setLines(lines.map((l, i) => (i === index ? { ...l, ...updates } : l)))
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await setBudget.mutateAsync({
        overall_amount: overallAmount.trim() ? overallAmount.trim() : null,
        lines: lines.map((l) => ({
          ...l,
          amount: parseFloat(String(l.amount || '0')).toFixed(2),
        })),
      })
      if (res.warning) {
        toast.warning(res.warning)
      } else {
        toast.success('Budget saved successfully')
      }
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to save budget'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <form onSubmit={handleSave}>
          <DialogHeader>
            <DialogTitle>Set Budget for {month}</DialogTitle>
            <DialogDescription>
              Configure an overall monthly spending limit and category-specific targets.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            <div className="space-y-2">
              <Label htmlFor="overall-amount">Overall Monthly Budget</Label>
              <Input
                id="overall-amount"
                type="number"
                step="0.01"
                min="0.01"
                placeholder="e.g. 50000.00"
                value={overallAmount}
                onChange={(e) => setOverallAmount(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Optional. If omitted, overall spend will still be tracked against category budgets.
              </p>
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label>Category Budgets</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleAddLine}
                  disabled={expenseCategories.length === 0}
                >
                  <Plus className="mr-1 size-3" />
                  Add Category
                </Button>
              </div>

              {lines.length === 0 ? (
                <div className="rounded-lg border border-dashed p-4 text-center text-sm text-muted-foreground">
                  No category budgets set. Click &quot;Add Category&quot; to set limits for individual spending categories.
                </div>
              ) : (
                <div className="space-y-3">
                  {lines.map((line, idx) => (
                    <div key={idx} className="flex items-center gap-2 rounded-lg border p-2 bg-muted/20">
                      <select
                        className="h-9 flex-1 rounded-md border bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                        value={line.category_id}
                        aria-label="Category"
                        onChange={(e) => handleLineChange(idx, { category_id: e.target.value })}
                      >
                        {expenseCategories.map((c) => (
                          <option key={c.value} value={c.value}>
                            {c.label}
                          </option>
                        ))}
                      </select>

                      <Input
                        type="number"
                        step="0.01"
                        min="0.01"
                        aria-label="Budget amount"
                        className="w-32"
                        placeholder="Amount"
                        value={line.amount}
                        onChange={(e) => handleLineChange(idx, { amount: e.target.value })}
                        required
                      />

                      <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        className="text-destructive hover:bg-destructive/10"
                        aria-label="Remove category"
                        onClick={() => handleRemoveLine(idx)}
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={setBudget.isPending}>
              {setBudget.isPending ? 'Saving...' : 'Save Budget'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
