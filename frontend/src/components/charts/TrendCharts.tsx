import { Bar, BarChart, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import { formatPercent } from '@/lib/format'
import type { MonthFigures } from '@/services/api/types'

import { CHART_COLORS, compactInr, num } from './ChartCard'
import { prefersReducedMotion } from './CategoryDonut'

const tooltipStyle = {
  backgroundColor: 'var(--popover)',
  color: 'var(--popover-foreground)',
  border: '1px solid var(--border)',
  borderRadius: 8,
}

export function IncomeExpenseChart({ months }: { months: MonthFigures[] }) {
  const { money } = useFormatters()
  const data = months.map((m) => ({ label: m.label.replace(' 20', " '"), income: num(m.income), expenses: num(m.expenses), src: m }))
  return (
    <div role="img" aria-label={`Income and expenses for ${months.length} months`} className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ left: 8, right: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
          <XAxis dataKey="label" stroke={CHART_COLORS.axis} tickLine={false} fontSize={12} />
          <YAxis stroke={CHART_COLORS.axis} tickFormatter={compactInr} width={56} fontSize={12} />
          <Tooltip contentStyle={tooltipStyle} formatter={(_v, name, item) => {
            const src = (item.payload as { src: MonthFigures }).src
            return [money(name === 'Income' ? src.income : src.expenses), name]
          }} />
          <Legend />
          <Bar dataKey="income" name="Income" fill={CHART_COLORS.income} radius={[3, 3, 0, 0]} isAnimationActive={!prefersReducedMotion()} />
          <Bar dataKey="expenses" name="Expenses" fill={CHART_COLORS.expense} radius={[3, 3, 0, 0]} isAnimationActive={!prefersReducedMotion()} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

export function SavingsTrendChart({ months }: { months: MonthFigures[] }) {
  const { money } = useFormatters()
  const data = months.map((m) => ({ label: m.label.replace(' 20', " '"), savings: num(m.savings), rate: num(m.savings_rate), src: m }))
  return (
    <div role="img" aria-label={`Savings and savings rate for ${months.length} months`} className="h-64 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ left: 8, right: 8 }}>
          <CartesianGrid vertical={false} stroke={CHART_COLORS.grid} />
          <XAxis dataKey="label" stroke={CHART_COLORS.axis} tickLine={false} fontSize={12} />
          <YAxis yAxisId="amt" stroke={CHART_COLORS.axis} tickFormatter={compactInr} width={56} fontSize={12} />
          <YAxis yAxisId="pct" orientation="right" stroke={CHART_COLORS.axis} tickFormatter={(v: number) => `${v}%`} width={44} fontSize={12} />
          <Tooltip contentStyle={tooltipStyle} formatter={(_v, name, item) => {
            const src = (item.payload as { src: MonthFigures }).src
            return name === 'Savings' ? [money(src.savings), name] : [formatPercent(src.savings_rate), name]
          }} />
          <Legend />
          <Bar yAxisId="amt" dataKey="savings" name="Savings" fill={CHART_COLORS.savings} radius={[3, 3, 0, 0]} isAnimationActive={!prefersReducedMotion()} />
          {/* connectNulls=false leaves a gap for months with zero income (rate is N/A) */}
          <Line yAxisId="pct" dataKey="rate" name="Savings rate" stroke={CHART_COLORS.rate} strokeWidth={2}
            dot={{ r: 3 }} connectNulls={false} type="monotone" isAnimationActive={!prefersReducedMotion()} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

export function MonthsTable({ months }: { months: MonthFigures[] }) {
  const { money } = useFormatters()
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Month</TableHead>
          <TableHead className="text-right">Income</TableHead>
          <TableHead className="text-right">Expenses</TableHead>
          <TableHead className="text-right">Savings</TableHead>
          <TableHead className="text-right">Savings rate</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {months.map((m) => (
          <TableRow key={m.month}>
            <TableCell>{m.label}</TableCell>
            <TableCell className="text-right tabular-nums">{money(m.income)}</TableCell>
            <TableCell className="text-right tabular-nums">{money(m.expenses)}</TableCell>
            <TableCell className="text-right tabular-nums">{money(m.savings)}</TableCell>
            <TableCell className="text-right tabular-nums">{formatPercent(m.savings_rate)}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
