import { useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
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
import type { AssetCreate } from '@/services/api/types'

import { useCreateAsset } from './api'

interface AssetFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const ASSET_TYPES = [
  { value: 'fixed_deposit', label: 'Fixed Deposit' },
  { value: 'gold', label: 'Gold / Precious Metals' },
  { value: 'real_estate', label: 'Real Estate / Property' },
  { value: 'ppf', label: 'PPF' },
  { value: 'epf', label: 'EPF' },
  { value: 'nps', label: 'NPS' },
  { value: 'mutual_fund', label: 'Mutual Funds' },
  { value: 'vehicle', label: 'Vehicle' },
  { value: 'other', label: 'Other Asset' },
]

export function AssetFormDialog({ open, onOpenChange }: AssetFormDialogProps) {
  const createAsset = useCreateAsset()

  const [name, setName] = useState('')
  const [type, setType] = useState('fixed_deposit')
  const [initialValue, setInitialValue] = useState('')
  const [asOf, setAsOf] = useState(() => new Date().toISOString().slice(0, 10))
  const [isLiquid, setIsLiquid] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload: AssetCreate = {
        name: name.trim(),
        type,
        current_value: initialValue,
        as_of: asOf,
        is_liquid: isLiquid,
        details: {},
      }
      await createAsset.mutateAsync(payload)
      toast.success('Asset created')
      setName('')
      setInitialValue('')
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create asset'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add Manual Asset</DialogTitle>
            <DialogDescription>
              Record an asset you own (fixed deposits, property, gold, retirement schemes) with dated valuations.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-1.5">
              <Label htmlFor="asset-name">Asset Name</Label>
              <Input
                id="asset-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. HDFC 2-Year FD or 50g Sovereign Gold Bond"
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="asset-type">Asset Type</Label>
              <select
                id="asset-type"
                className="h-9 w-full rounded-md border bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={type}
                onChange={(e) => setType(e.target.value)}
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="asset-value">Current Value (₹)</Label>
                <Input
                  id="asset-value"
                  type="number"
                  step="0.01"
                  min="0.01"
                  placeholder="205000.00"
                  value={initialValue}
                  onChange={(e) => setInitialValue(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="asset-as-of">Valuation Date</Label>
                <Input
                  id="asset-as-of"
                  type="date"
                  value={asOf}
                  onChange={(e) => setAsOf(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="flex items-center space-x-2 pt-1">
              <Checkbox
                id="asset-liquid"
                checked={isLiquid}
                onCheckedChange={(checked) => setIsLiquid(Boolean(checked))}
              />
              <Label htmlFor="asset-liquid" className="text-xs font-normal">
                Liquid Asset (can be quickly converted to cash for emergency fund)
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createAsset.isPending}>
              {createAsset.isPending ? 'Adding...' : 'Add Asset'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
