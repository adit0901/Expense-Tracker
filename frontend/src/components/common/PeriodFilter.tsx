import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { PERIOD_OPTIONS, type PeriodKind, usePeriodParam } from '@/lib/period'

export function PeriodFilter({ defaultKind = 'this_month' }: { defaultKind?: PeriodKind }) {
  const { period, start, end, setPeriod, ready } = usePeriodParam(defaultKind)
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div className="grid gap-1">
        <Label htmlFor="period-select" className="text-xs">Period</Label>
        <Select value={period} onValueChange={(v) => setPeriod(v as PeriodKind, { start, end })}>
          <SelectTrigger id="period-select" className="w-48">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map((o) => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {period === 'custom' && (
        <>
          <div className="grid gap-1">
            <Label htmlFor="period-start" className="text-xs">From</Label>
            <Input id="period-start" type="date" className="w-40" value={start ?? ''}
              onChange={(e) => setPeriod('custom', { start: e.target.value, end })} />
          </div>
          <div className="grid gap-1">
            <Label htmlFor="period-end" className="text-xs">To</Label>
            <Input id="period-end" type="date" className="w-40" value={end ?? ''}
              onChange={(e) => setPeriod('custom', { start, end: e.target.value })} />
          </div>
          {!ready && <p className="text-xs text-muted-foreground">Choose a start and end date.</p>}
        </>
      )}
    </div>
  )
}
