import { Plus } from 'lucide-react'
import { useState } from 'react'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import type { AssetOut } from '@/services/api/types'

import { useAddAssetValuation, useAssetValuations, useCloseAsset } from './api'

interface ValuationHistoryModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  asset: AssetOut
}

export function ValuationHistoryModal({
  open,
  onOpenChange,
  asset,
}: ValuationHistoryModalProps) {
  const { money, date } = useFormatters()
  const valuationsQuery = useAssetValuations(asset.id)
  const addValuation = useAddAssetValuation(asset.id)
  const closeAsset = useCloseAsset(asset.id)

  const [newValue, setNewValue] = useState('')
  const [newDate, setNewDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [closingDate, setClosingDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [showCloseForm, setShowCloseForm] = useState(false)

  const valuations = valuationsQuery.data ?? []

  const handleAddValuation = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await addValuation.mutateAsync({
        value: newValue,
        as_of: newDate,
      })
      toast.success('Valuation recorded')
      setNewValue('')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to record valuation'
      toast.error(msg)
    }
  }

  const handleCloseAsset = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await closeAsset.mutateAsync({
        closed_at: closingDate,
      })
      toast.success('Asset closed')
      setShowCloseForm(false)
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to close asset'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>Valuation History: {asset.name}</DialogTitle>
            {asset.closed_at ? (
              <Badge variant="secondary">Closed</Badge>
            ) : (
              <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                Active
              </Badge>
            )}
          </div>
          <DialogDescription>
            Historical valuations are preserved for accurate point-in-time net worth reporting.
          </DialogDescription>
        </DialogHeader>

        {!asset.closed_at && (
          <div className="rounded-lg border bg-muted/20 p-3 space-y-3">
            <h4 className="text-xs font-semibold uppercase text-muted-foreground">
              Record New Valuation
            </h4>
            <form onSubmit={handleAddValuation} className="flex items-end gap-2">
              <div className="flex-1 space-y-1">
                <Label htmlFor="val-date" className="text-xs">
                  Date
                </Label>
                <Input
                  id="val-date"
                  type="date"
                  className="h-8 text-xs"
                  value={newDate}
                  onChange={(e) => setNewDate(e.target.value)}
                  required
                />
              </div>
              <div className="flex-1 space-y-1">
                <Label htmlFor="val-amt" className="text-xs">
                  Value (₹)
                </Label>
                <Input
                  id="val-amt"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="210000.00"
                  className="h-8 text-xs"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  required
                />
              </div>
              <Button type="submit" size="sm" className="h-8 text-xs" disabled={addValuation.isPending}>
                <Plus className="mr-1 size-3" />
                Add
              </Button>
            </form>
          </div>
        )}

        <div className="py-2">
          {valuationsQuery.isPending ? (
            <LoadingBlock label="Loading valuations..." />
          ) : valuations.length === 0 ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              No valuation entries recorded.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Valuation Date</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                  <TableHead className="text-right">Recorded At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {valuations.map((v) => (
                  <TableRow key={v.id}>
                    <TableCell className="font-medium">{date(String(v.as_of))}</TableCell>
                    <TableCell className="text-right font-semibold tabular-nums">
                      {money(String(v.value))}
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {date(String(v.created_at))}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>

        {!asset.closed_at && (
          <div className="border-t pt-3">
            {!showCloseForm ? (
              <Button
                variant="outline"
                size="sm"
                className="text-xs text-destructive hover:bg-destructive/10"
                onClick={() => setShowCloseForm(true)}
              >
                Close Asset (Sold / Liquidated)
              </Button>
            ) : (
              <form onSubmit={handleCloseAsset} className="space-y-3 rounded-lg border border-destructive/20 bg-destructive/5 p-3">
                <p className="text-xs text-muted-foreground">
                  Closing keeps historical valuations for past reports but excludes this asset from current and future net worth.
                </p>
                <div className="flex items-end gap-2">
                  <div className="flex-1 space-y-1">
                    <Label htmlFor="close-date" className="text-xs">
                      Closing Date
                    </Label>
                    <Input
                      id="close-date"
                      type="date"
                      className="h-8 text-xs"
                      value={closingDate}
                      onChange={(e) => setClosingDate(e.target.value)}
                      required
                    />
                  </div>
                  <Button
                    type="submit"
                    variant="destructive"
                    size="sm"
                    className="h-8 text-xs"
                    disabled={closeAsset.isPending}
                  >
                    Confirm Close
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-8 text-xs"
                    onClick={() => setShowCloseForm(false)}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

