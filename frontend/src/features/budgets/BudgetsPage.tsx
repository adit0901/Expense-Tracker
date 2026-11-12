import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  Bell,
  Copy,
  Edit3,
} from 'lucide-react'
import { useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { EmptyState, ErrorState, LoadingBlock, PageHeader } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { categoryOptions, useCategories } from '@/features/categories/api'
import { useFormatters } from '@/features/settings/usePreferences'
import { formatPercent } from '@/lib/format'
import { cn } from '@/lib/utils'

import { useBudget, useBudgetAlerts, useBudgetComparison } from './api'
import { BudgetEditDialog } from './BudgetEditDialog'
import { CopyForwardDialog } from './CopyForwardDialog'

function getCurrentMonth(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split('-').map(Number)
  if (!y || !m) return month
  const d = new Date(Date.UTC(y, m - 1 + delta, 1))
  const ny = d.getUTCFullYear()
  const nm = String(d.getUTCMonth() + 1).padStart(2, '0')
  return `${ny}-${nm}`
}

export function BudgetsPage() {
  const { money, date } = useFormatters()
  const [selectedMonth, setSelectedMonth] = useState<string>(getCurrentMonth)
  const [editOpen, setEditOpen] = useState(false)
  const [copyOpen, setCopyOpen] = useState(false)
  const [comparisonMonths, setComparisonMonths] = useState<number>(6)
  const [comparisonCategory, setComparisonCategory] = useState<string>('')

  const budgetQuery = useBudget(selectedMonth)
  const alertsQuery = useBudgetAlerts(selectedMonth)
  const comparisonQuery = useBudgetComparison(comparisonMonths, comparisonCategory || undefined)
  const categoriesQuery = useCategories()

  const expenseCategories = categoryOptions(categoriesQuery.data ?? [], 'expense')
  const budget = budgetQuery.data
  const lines = budget?.lines ?? []
  const alerts = alertsQuery.data ?? []

  const hasBudgetSet = Boolean(budget?.overall_amount || lines.length > 0)

  return (
    <div className="space-y-6">
      <PageHeader
        title="Budgets"
        description="Set monthly spending limits for categories and track utilization before overspending."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center rounded-md border bg-background shadow-xs">
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label="Previous month"
                onClick={() => setSelectedMonth((m) => shiftMonth(m, -1))}
              >
                <ArrowLeft className="size-4" />
              </Button>
              <input
                type="month"
                aria-label="Select month"
                className="border-none bg-transparent px-2 py-1 text-sm font-medium focus:outline-none"
                value={selectedMonth}
                onChange={(e) => e.target.value && setSelectedMonth(e.target.value)}
              />
              <Button
                variant="ghost"
                size="icon"
                className="h-8 w-8"
                aria-label="Next month"
                onClick={() => setSelectedMonth((m) => shiftMonth(m, 1))}
              >
                <ArrowRight className="size-4" />
              </Button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setCopyOpen(true)}
            >
              <Copy className="mr-1.5 size-3.5" />
              Copy Forward
            </Button>
            <Button
              size="sm"
              onClick={() => setEditOpen(true)}
            >
              <Edit3 className="mr-1.5 size-3.5" />
              {hasBudgetSet ? 'Edit Budget' : 'Set Budget'}
            </Button>
          </div>
        }
      />

      {budget?.warning && (
        <div
          role="alert"
          className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-600 dark:text-amber-400"
        >
          <AlertTriangle className="size-4 shrink-0" />
          <span>{budget.warning}</span>
        </div>
      )}

      {budgetQuery.isPending ? (
        <LoadingBlock label="Loading budget..." />
      ) : budgetQuery.isError ? (
        <ErrorState error={budgetQuery.error} onRetry={() => void budgetQuery.refetch()} />
      ) : !hasBudgetSet || !budget ? (
        <EmptyState
          title={`No budget set for ${selectedMonth}`}
          description="Plan your monthly expenses by setting category budgets or copy previous month's budget."
          action={
            <div className="flex gap-2">
              <Button onClick={() => setEditOpen(true)}>Set Budget</Button>
              <Button variant="outline" onClick={() => setCopyOpen(true)}>
                Copy from Previous Month
              </Button>
            </div>
          }
        />
      ) : (
        <>
          {/* Overall Budget Overview Card */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base font-semibold">Overall Budget</CardTitle>
                {budget.overall_is_over_budget && (
                  <Badge variant="destructive">Over Budget</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-muted-foreground">Budgeted</p>
                  <p className="text-lg font-semibold tabular-nums">
                    {budget.overall_amount ? money(budget.overall_amount) : 'Not set'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Actual Spent</p>
                  <p className="text-lg font-semibold tabular-nums">
                    {money(budget.overall_actual)}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Remaining</p>
                  <p
                    className={cn(
                      'text-lg font-semibold tabular-nums',
                      budget.overall_is_over_budget ? 'text-destructive' : 'text-success',
                    )}
                  >
                    {budget.overall_remaining ? money(budget.overall_remaining) : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Utilization</p>
                  <p className="text-lg font-semibold tabular-nums">
                    {budget.overall_utilization ? formatPercent(budget.overall_utilization) : '—'}
                  </p>
                </div>
              </div>

              {budget.overall_utilization && (
                <div className="space-y-1">
                  <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                    <div
                      className={cn(
                        'h-full transition-all',
                        budget.overall_is_over_budget
                          ? 'bg-destructive'
                          : Number(budget.overall_utilization) > 80
                            ? 'bg-amber-500'
                            : 'bg-primary',
                      )}
                      style={{
                        width: `${Math.min(100, Math.max(0, Number(budget.overall_utilization)))}%`,
                      }}
                      role="progressbar"
                      aria-valuenow={Number(budget.overall_utilization)}
                      aria-valuemin={0}
                      aria-valuemax={100}
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Category Budgets Table */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-semibold">Category Budgets</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              {lines.length === 0 ? (
                <div className="p-6 text-center text-sm text-muted-foreground">
                  No individual category limits configured for this month.
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Category</TableHead>
                      <TableHead className="text-right">Budget</TableHead>
                      <TableHead className="text-right">Actual</TableHead>
                      <TableHead className="w-48 text-center">Utilization</TableHead>
                      <TableHead className="text-right">Remaining</TableHead>
                      <TableHead className="text-center">Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {lines.map((line) => {
                      const utilNum = Number(line.utilization)
                      return (
                        <TableRow key={line.id}>
                          <TableCell className="font-medium">{line.category_name}</TableCell>
                          <TableCell className="text-right tabular-nums">{money(line.amount)}</TableCell>
                          <TableCell className="text-right tabular-nums">{money(line.actual)}</TableCell>
                          <TableCell>
                            <div className="space-y-1">
                              <div className="flex justify-between text-xs tabular-nums text-muted-foreground">
                                <span>{formatPercent(line.utilization)}</span>
                              </div>
                              <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                                <div
                                  className={cn(
                                    'h-full transition-all',
                                    line.is_over_budget
                                      ? 'bg-destructive'
                                      : utilNum > 80
                                        ? 'bg-amber-500'
                                        : 'bg-primary',
                                  )}
                                  style={{ width: `${Math.min(100, Math.max(0, utilNum))}%` }}
                                  role="progressbar"
                                  aria-valuenow={utilNum}
                                  aria-valuemin={0}
                                  aria-valuemax={100}
                                />
                              </div>
                            </div>
                          </TableCell>
                          <TableCell
                            className={cn(
                              'text-right tabular-nums font-medium',
                              line.is_over_budget ? 'text-destructive' : 'text-foreground',
                            )}
                          >
                            {money(line.remaining)}
                          </TableCell>
                          <TableCell className="text-center">
                            {line.is_over_budget ? (
                              <Badge variant="destructive">Over budget</Badge>
                            ) : utilNum >= 80 ? (
                              <Badge variant="outline" className="border-amber-500 text-amber-500">
                                Warning
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                                On track
                              </Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {/* Spending Alerts Section */}
      {alerts.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Bell className="size-4 text-amber-500" />
              <CardTitle className="text-base font-semibold">Active Spending Alerts</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <ul className="divide-y" aria-label="Active alerts">
              {alerts.map((alert) => (
                <li key={alert.id} className="flex items-center justify-between p-4 text-sm">
                  <div className="flex items-center gap-2">
                    <AlertTriangle
                      className={cn(
                        'size-4',
                        alert.threshold >= 100 ? 'text-destructive' : 'text-amber-500',
                      )}
                    />
                    <span>
                      <strong className="font-medium">
                        {alert.category_name ?? 'Overall budget'}
                      </strong>{' '}
                      crossed {alert.threshold}% threshold
                    </span>
                  </div>
                  <span className="text-xs text-muted-foreground">{date(alert.triggered_at)}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Comparison Chart Section */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle className="text-base font-semibold">Budget vs Actual Comparison</CardTitle>
            <div className="flex items-center gap-2">
              <select
                aria-label="Category filter"
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={comparisonCategory}
                onChange={(e) => setComparisonCategory(e.target.value)}
              >
                <option value="">All Categories (Overall)</option>
                {expenseCategories.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>

              <select
                aria-label="Comparison range"
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={comparisonMonths}
                onChange={(e) => setComparisonMonths(Number(e.target.value))}
              >
                <option value={6}>Last 6 Months</option>
                <option value={12}>Last 12 Months</option>
              </select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {comparisonQuery.isPending ? (
            <LoadingBlock label="Loading comparison..." />
          ) : comparisonQuery.isError ? (
            <ErrorState error={comparisonQuery.error} onRetry={() => void comparisonQuery.refetch()} />
          ) : (
            <div className="space-y-6">
              <div className="h-64 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonQuery.data?.months ?? []}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="month_label" />
                    <YAxis />
                    <Tooltip
                      formatter={(val: unknown) => [money(String(val ?? '0')), '']}
                    />
                    <Legend />
                    <Bar dataKey="budget" name="Budget" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="actual" name="Actual" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Month</TableHead>
                    <TableHead className="text-right">Budget</TableHead>
                    <TableHead className="text-right">Actual</TableHead>
                    <TableHead className="text-right">Utilization</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(comparisonQuery.data?.months ?? []).map((m) => (
                    <TableRow key={m.month}>
                      <TableCell className="font-medium">{m.month_label}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {m.budget ? money(m.budget) : 'No budget'}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">{money(m.actual)}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {m.utilization ? formatPercent(m.utilization) : '—'}
                      </TableCell>
                      <TableCell className="text-center">
                        {!m.budget ? (
                          <Badge variant="outline">No budget</Badge>
                        ) : m.is_over_budget ? (
                          <Badge variant="destructive">Over budget</Badge>
                        ) : (
                          <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                            On track
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <BudgetEditDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        month={selectedMonth}
        currentBudget={budget}
      />
      <CopyForwardDialog
        open={copyOpen}
        onOpenChange={setCopyOpen}
        currentMonth={selectedMonth}
      />
    </div>
  )
}
