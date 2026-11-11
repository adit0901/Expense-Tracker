import { useQuery } from '@tanstack/react-query'
import { Download } from 'lucide-react'
import { Link } from 'react-router'
import { toast } from 'sonner'

import { ChartCard } from '@/components/charts/ChartCard'
import { IncomeExpenseChart, MonthsTable, SavingsTrendChart } from '@/components/charts/TrendCharts'
import { EmptyState, ErrorState, LoadingBlock, errorMessage } from '@/components/common/states'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import { PAYMENT_METHOD_LABELS, formatPercent } from '@/lib/format'
import type { PeriodQuery } from '@/lib/period'
import { qk } from '@/lib/queryKeys'
import { api, download } from '@/services/api/client'
import type { ExpenseReport, IncomeReport, SavingsTrend } from '@/services/api/types'

export function ExportButton({ path, query, name }: { path: string; query: PeriodQuery; name: string }) {
  return (
    <Button variant="outline" size="sm"
      onClick={() => void download(path, query, name).catch((e) => toast.error(errorMessage(e)))}>
      <Download aria-hidden /> Export CSV
    </Button>
  )
}

export function useIncomeReport(query: PeriodQuery, enabled = true) {
  return useQuery({ queryKey: [...qk.reports, 'income', query], queryFn: () => api.get<IncomeReport>('/reports/income', query), enabled })
}
export function useExpenseReport(query: PeriodQuery, enabled = true) {
  return useQuery({ queryKey: [...qk.reports, 'expenses', query], queryFn: () => api.get<ExpenseReport>('/reports/expenses', query), enabled })
}
export function useSavingsTrend(query: PeriodQuery, enabled = true) {
  return useQuery({ queryKey: [...qk.reports, 'savings', query], queryFn: () => api.get<SavingsTrend>('/reports/savings-trend', { ...query, months: 12 }), enabled })
}

function drillLink(categoryId: string | null, r: { period: { start: string; end: string } }, type: string): string {
  const p = new URLSearchParams({ date_from: r.period.start, date_to: r.period.end })
  if (categoryId) p.set('category_id', categoryId)
  p.append('type', type)
  return `/transactions?${p.toString()}`
}

export function IncomeReportView({ query, enabled = true }: { query: PeriodQuery; enabled?: boolean }) {
  const report = useIncomeReport(query, enabled)
  const { money } = useFormatters()
  if (report.isPending) return <LoadingBlock label="Loading income report" />
  if (report.isError) return <ErrorState error={report.error} onRetry={() => void report.refetch()} />
  const r = report.data
  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-lg">Total income <span className="font-semibold tabular-nums">{money(r.total_income)}</span> <span className="text-sm text-muted-foreground">({r.period.label})</span></p>
        <ExportButton path="/reports/income/export.csv" query={query} name="income.csv" />
      </div>
      {r.total_income === '0.00' ? <EmptyState title="No income recorded in this period" /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle><h2 className="text-base">By source</h2></CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader><TableRow><TableHead>Source</TableHead><TableHead className="text-right">Total</TableHead><TableHead className="text-right">Share</TableHead></TableRow></TableHeader>
                <TableBody>{r.by_source.map((s) => (
                  <TableRow key={s.source_id ?? 'none'}><TableCell>{s.name}</TableCell><TableCell className="text-right tabular-nums">{money(s.total)}</TableCell><TableCell className="text-right">{formatPercent(s.share)}</TableCell></TableRow>
                ))}</TableBody>
              </Table>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle><h2 className="text-base">By category</h2></CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader><TableRow><TableHead>Category</TableHead><TableHead className="text-right">Total</TableHead><TableHead className="text-right">Share</TableHead></TableRow></TableHeader>
                <TableBody>{r.by_category.map((c) => (
                  <TableRow key={c.category_id ?? c.name}><TableCell><Link className="underline-offset-4 hover:underline" to={drillLink(c.category_id, r, 'income')}>{c.name}</Link></TableCell>
                    <TableCell className="text-right tabular-nums">{money(c.total)}</TableCell><TableCell className="text-right">{formatPercent(c.share)}</TableCell></TableRow>
                ))}</TableBody>
              </Table>
            </CardContent>
          </Card>
          <Card className="lg:col-span-2">
            <CardHeader><CardTitle><h2 className="text-base">Monthly income and salary breakdown</h2></CardTitle></CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader><TableRow><TableHead>Month</TableHead><TableHead className="text-right">Net income</TableHead><TableHead className="text-right">Salary gross</TableHead><TableHead className="text-right">Deductions</TableHead><TableHead className="text-right">Salary net</TableHead></TableRow></TableHeader>
                <TableBody>
                  {r.months.map((m, i) => {
                    const s = r.salary.months[i]
                    return (
                      <TableRow key={m.month}><TableCell>{m.label}</TableCell><TableCell className="text-right tabular-nums">{money(m.income)}</TableCell>
                        <TableCell className="text-right tabular-nums">{money(s?.gross)}</TableCell><TableCell className="text-right tabular-nums">{money(s?.total_deductions)}</TableCell>
                        <TableCell className="text-right tabular-nums">{money(s?.net)}</TableCell></TableRow>
                    )
                  })}
                  <TableRow className="font-semibold"><TableCell>Total</TableCell><TableCell className="text-right tabular-nums">{money(r.total_income)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.salary.gross)}</TableCell><TableCell className="text-right tabular-nums">{money(r.salary.total_deductions)}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(r.salary.net)}</TableCell></TableRow>
                </TableBody>
              </Table>
              {r.salary.deductions.length > 0 && (
                <p className="mt-3 text-sm text-muted-foreground">
                  Deductions: {r.salary.deductions.map((d) => `${d.name} ${money(d.amount)}`).join(' · ')}. Deductions are not counted as expenses.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export function ExpenseReportView({ query, enabled = true }: { query: PeriodQuery; enabled?: boolean }) {
  const report = useExpenseReport(query, enabled)
  const { money } = useFormatters()
  if (report.isPending) return <LoadingBlock label="Loading expense report" />
  if (report.isError) return <ErrorState error={report.error} onRetry={() => void report.refetch()} />
  const r = report.data
  return (
    <div className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-lg">Total expenses <span className="font-semibold tabular-nums">{money(r.total_expenses)}</span> <span className="text-sm text-muted-foreground">({r.period.label})</span></p>
        <ExportButton path="/reports/expenses/export.csv" query={query} name="expenses.csv" />
      </div>
      {r.total_expenses === '0.00' && r.by_category.length === 0 ? <EmptyState title="No expenses recorded in this period" /> : (
        <div className="grid gap-6 lg:grid-cols-2">
          <Card>
            <CardHeader><CardTitle><h2 className="text-base">By category</h2></CardTitle></CardHeader>
            <CardContent>
              <Table>
                <TableHeader><TableRow><TableHead>Category</TableHead><TableHead className="text-right">Total</TableHead><TableHead className="text-right">Share</TableHead></TableRow></TableHeader>
                <TableBody>{r.by_category.flatMap((c) => [
                  <TableRow key={c.category_id}><TableCell><Link className="underline-offset-4 hover:underline" to={drillLink(c.category_id, r, 'expense')}>{c.name}</Link></TableCell>
                    <TableCell className="text-right tabular-nums">{money(c.total)}</TableCell><TableCell className="text-right">{formatPercent(c.share)}</TableCell></TableRow>,
                  ...c.subcategories.map((s) => (
                    <TableRow key={s.category_id}><TableCell className="pl-8 text-muted-foreground">{s.name}</TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">{money(s.total)}</TableCell><TableCell className="text-right text-muted-foreground">{formatPercent(s.share)}</TableCell></TableRow>
                  )),
                ])}</TableBody>
              </Table>
            </CardContent>
          </Card>
          <Card>
            <CardHeader><CardTitle><h2 className="text-base">By payment method</h2></CardTitle></CardHeader>
            <CardContent>
              <Table aria-label="Expenses by payment method">
                <TableHeader><TableRow><TableHead>Method</TableHead><TableHead className="text-right">Total</TableHead><TableHead className="text-right">Share</TableHead></TableRow></TableHeader>
                <TableBody>
                  {r.by_payment_method.map((m) => (
                    <TableRow key={m.method}><TableCell>{PAYMENT_METHOD_LABELS[m.method] ?? m.method}</TableCell>
                      <TableCell className="text-right tabular-nums">{money(m.total)}</TableCell><TableCell className="text-right">{formatPercent(m.share)}</TableCell></TableRow>
                  ))}
                  <TableRow className="font-semibold"><TableCell>Total</TableCell><TableCell className="text-right tabular-nums">{money(r.total_expenses)}</TableCell><TableCell /></TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}

export function SavingsTrendView({ query, enabled = true }: { query: PeriodQuery; enabled?: boolean }) {
  const trend = useSavingsTrend(query, enabled)
  const months = trend.data?.months ?? []
  const empty = months.every((m) => m.income === '0.00' && m.expenses === '0.00')
  return (
    <div className="grid gap-6">
      <div className="flex justify-end"><ExportButton path="/reports/savings-trend/export.csv" query={query} name="savings-trend.csv" /></div>
      <ChartCard title="Savings and savings rate" isLoading={trend.isPending} error={trend.error} onRetry={() => void trend.refetch()}
        isEmpty={empty} table={<MonthsTable months={months} />}>
        <SavingsTrendChart months={months} />
      </ChartCard>
      <ChartCard title="Income vs expenses" isLoading={trend.isPending} error={trend.error} onRetry={() => void trend.refetch()}
        isEmpty={empty} table={<MonthsTable months={months} />}>
        <IncomeExpenseChart months={months} />
      </ChartCard>
    </div>
  )
}
