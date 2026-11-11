import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'

import { useFormatters } from '@/features/settings/usePreferences'
import { formatPercent } from '@/lib/format'
import type { CategoryBreakdown } from '@/services/api/types'

import { CATEGORY_COLORS, OTHER_COLOR, num } from './ChartCard'

type Row = CategoryBreakdown['categories'][number]

export function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function colorFor(row: Row, index: number): string {
  return row.is_other ? OTHER_COLOR : CATEGORY_COLORS[index % CATEGORY_COLORS.length]!
}

/** Donut plus an accessible legend; selecting a category drills down to its transactions. */
export function CategoryDonut({ rows, onSelect }: { rows: Row[]; onSelect: (row: Row) => void }) {
  const { money } = useFormatters()
  const data = rows.map((r, i) => ({ name: r.name, value: num(r.total) ?? 0, row: r, color: colorFor(r, i) }))
  return (
    <div className="flex flex-wrap items-center gap-4">
      <div role="img" aria-label="Expenses by category" className="mx-auto h-52 w-52 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius="55%" outerRadius="90%" paddingAngle={1}
              onClick={(d: { payload?: { row: Row } }) => d.payload && onSelect(d.payload.row)} cursor="pointer" stroke="var(--card)"
              isAnimationActive={!prefersReducedMotion()}>
              {data.map((d) => <Cell key={d.name} fill={d.color} />)}
            </Pie>
            <Tooltip formatter={(_v, _n, item) => {
              const r = (item.payload as { row: Row }).row
              return [`${money(r.total)} (${formatPercent(r.share)})`, r.name]
            }} contentStyle={{ backgroundColor: 'var(--popover)', color: 'var(--popover-foreground)', border: '1px solid var(--border)', borderRadius: 8 }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <ul className="grid min-w-0 flex-1 basis-64 gap-1" aria-label="Category legend">
        {data.map((d) => (
          <li key={d.name}>
            <button type="button" disabled={d.row.is_other}
              className="flex w-full items-center gap-2 rounded px-2 py-1 text-left text-sm outline-none hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-default disabled:hover:bg-transparent"
              onClick={() => onSelect(d.row)}>
              {/* Whitespace nodes separate the parts of the accessible name; flex layout ignores them. */}
              {!d.row.is_other && <span className="sr-only">View transactions for</span>}{' '}
              <span className="size-3 shrink-0 rounded-sm" style={{ backgroundColor: d.color }} aria-hidden />
              <span className="min-w-0 flex-1 truncate">{d.name}</span>{' '}
              <span className="tabular-nums">{money(d.row.total)}</span>{' '}
              <span className="w-14 text-right text-xs text-muted-foreground tabular-nums">{formatPercent(d.row.share)}</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
