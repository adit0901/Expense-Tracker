import { BarChart3, Table2 } from 'lucide-react'
import { useState } from 'react'

import { EmptyState, ErrorState } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

/** Card wrapper giving every chart loading/empty/error states and a table alternative. */
export function ChartCard({
  title,
  isLoading,
  error,
  onRetry,
  isEmpty,
  emptyTitle = 'No data for this period',
  emptyAction,
  table,
  children,
  className,
}: {
  title: string
  isLoading?: boolean
  error?: unknown
  onRetry?: () => void
  isEmpty?: boolean
  emptyTitle?: string
  emptyAction?: React.ReactNode
  table: React.ReactNode
  children: React.ReactNode
  className?: string
}) {
  const [asTable, setAsTable] = useState(false)
  return (
    <Card className={className}>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle><h2 className="text-base">{title}</h2></CardTitle>
        {!isLoading && !error && !isEmpty && (
          <Button variant="ghost" size="sm" onClick={() => setAsTable((v) => !v)} aria-pressed={asTable}>
            {asTable ? <BarChart3 aria-hidden /> : <Table2 aria-hidden />}
            {asTable ? 'Show chart' : 'Show table'}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <Skeleton className="h-64 w-full" aria-label={`Loading ${title}`} />
        ) : error ? (
          <ErrorState error={error} onRetry={onRetry} />
        ) : isEmpty ? (
          <EmptyState title={emptyTitle} action={emptyAction} />
        ) : asTable ? (
          <div className="overflow-x-auto">{table}</div>
        ) : (
          children
        )}
      </CardContent>
    </Card>
  )
}

/** Recharts needs numbers for geometry; values are display-only and never summed. */
export function num(v: string | null | undefined): number | null {
  if (v === null || v === undefined) return null
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

export const CHART_COLORS = {
  income: 'var(--chart-income)',
  expense: 'var(--chart-expense)',
  savings: 'var(--chart-savings)',
  rate: 'var(--chart-rate)',
  grid: 'var(--chart-grid)',
  axis: 'var(--chart-axis)',
}

export const CATEGORY_COLORS = ['var(--chart-1)', 'var(--chart-2)', 'var(--chart-3)', 'var(--chart-4)',
  'var(--chart-5)', 'var(--chart-6)']
export const OTHER_COLOR = 'var(--chart-other)'

export function compactInr(n: number): string {
  const abs = Math.abs(n)
  if (abs >= 1e7) return `₹${(n / 1e7).toFixed(1)}Cr`
  if (abs >= 1e5) return `₹${(n / 1e5).toFixed(1)}L`
  if (abs >= 1e3) return `₹${(n / 1e3).toFixed(0)}K`
  return `₹${n}`
}
