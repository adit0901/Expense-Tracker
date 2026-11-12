import { useQuery } from '@tanstack/react-query'
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  ChevronRight,
  CreditCard,
  Landmark,
  PiggyBank,
  Plus,
  Scale,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { CategoryDonut } from '@/components/charts/CategoryDonut'
import { ChartCard } from '@/components/charts/ChartCard'
import { IncomeExpenseChart, MonthsTable, SavingsTrendChart } from '@/components/charts/TrendCharts'
import { PeriodFilter } from '@/components/common/PeriodFilter'
import { EmptyState, ErrorState, PageHeader } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { AccountFormDialog } from '@/features/accounts/AccountFormDialog'
import { useFormatters } from '@/features/settings/usePreferences'
import { type TxnPage } from '@/features/transactions/api'
import { TransactionFormDialog } from '@/features/transactions/TransactionFormDialog'
import { formatChange, formatPercent } from '@/lib/format'
import { usePeriodParam } from '@/lib/period'
import { qk } from '@/lib/queryKeys'
import { cn } from '@/lib/utils'
import { api } from '@/services/api/client'
import type { CategoryBreakdown, Overview, SavingsTrend, Tile } from '@/services/api/types'

type TileKey = 'income' | 'expenses' | 'savings' | 'savings_rate' | 'liquid_funds'
const TILES: { key: TileKey; label: string; goodWhenUp: boolean; percent?: boolean }[] = [
  { key: 'income', label: 'Total income', goodWhenUp: true },
  { key: 'expenses', label: 'Total expenses', goodWhenUp: false },
  { key: 'savings', label: 'Savings', goodWhenUp: true },
  { key: 'savings_rate', label: 'Savings rate', goodWhenUp: true, percent: true },
  { key: 'liquid_funds', label: 'Liquid funds', goodWhenUp: true },
]

const ALLOCATION_COLORS = [
  '#3b82f6',
  '#10b981',
  '#f59e0b',
  '#8b5cf6',
  '#ec4899',
  '#06b6d4',
  '#f97316',
]

function KpiTile({
  label,
  tile,
  goodWhenUp,
  percent,
  previousLabel,
}: {
  label: string
  tile: Tile
  goodWhenUp: boolean
  percent?: boolean
  previousLabel: string
}) {
  const { money } = useFormatters()
  const change = tile.change
  const up = change !== null && change !== undefined && !change.startsWith('-') && change !== '0.00'
  const down = change !== null && change !== undefined && change.startsWith('-')
  const good = (up && goodWhenUp) || (down && !goodWhenUp)
  const bad = (down && goodWhenUp) || (up && !goodWhenUp)
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="mt-1 text-xl font-semibold tabular-nums">
          {percent ? formatPercent(tile.value) : money(tile.value)}
        </p>
        <p
          className={cn(
            'mt-1 flex items-center gap-1 text-xs',
            good && 'text-success',
            bad && 'text-destructive',
            !good && !bad && 'text-muted-foreground',
          )}
        >
          {up && <ArrowUpRight className="size-3" aria-hidden />}
          {down && <ArrowDownRight className="size-3" aria-hidden />}
          <span>{formatChange(change, tile.change_kind)}</span>
          <span className="text-muted-foreground">vs {previousLabel}</span>
        </p>
      </CardContent>
    </Card>
  )
}

export function OverviewPage() {
  const { query, ready } = usePeriodParam('this_month')
  const navigate = useNavigate()
  const { money, date } = useFormatters()
  const [addTxn, setAddTxn] = useState(false)
  const [addAccount, setAddAccount] = useState(false)

  const overview = useQuery({
    queryKey: [...qk.dashboard, 'overview', query],
    queryFn: () => api.get<Overview>('/dashboard/overview', query),
    enabled: ready,
  })
  const trends = useQuery({
    queryKey: [...qk.dashboard, 'trends', query],
    queryFn: () => api.get<SavingsTrend>('/dashboard/trends', { ...query, months: 12 }),
    enabled: ready,
  })
  const breakdown = useQuery({
    queryKey: [...qk.dashboard, 'breakdown', query],
    queryFn: () => api.get<CategoryBreakdown>('/dashboard/category-breakdown', query),
    enabled: ready,
  })
  const recent = useQuery({
    queryKey: [...qk.transactions, 'recent'],
    queryFn: () => api.page<TxnPage>('/transactions', { page_size: 10, sort: '-date' }),
  })

  const ov = overview.data
  const isNewUser = ov && !ov.has_transactions
  const months = trends.data?.months ?? []
  const trendEmpty = months.every((m) => m.income === '0.00' && m.expenses === '0.00')

  const drillDown = (row: CategoryBreakdown['categories'][number]) => {
    if (!row.category_id || !ov) return
    const p = new URLSearchParams({
      category_id: row.category_id,
      date_from: ov.period.start,
      date_to: ov.period.end,
    })
    p.append('type', 'expense')
    navigate(`/transactions?${p.toString()}`)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Overview"
        description={ov ? ov.period.label : undefined}
        actions={<PeriodFilter />}
      />

      {isNewUser && (
        <EmptyState
          title="Welcome to FinTrack"
          description={
            ov.has_accounts
              ? 'Add your first income or expense to see your dashboard come alive.'
              : 'Start by adding an account (bank, cash, card or wallet), then record your first transaction.'
          }
          action={
            <div className="flex flex-wrap justify-center gap-2">
              {!ov.has_accounts && (
                <Button onClick={() => setAddAccount(true)}>
                  <Plus aria-hidden /> Add account
                </Button>
              )}
              <Button
                variant={ov.has_accounts ? 'default' : 'outline'}
                onClick={() => setAddTxn(true)}
              >
                <Plus aria-hidden /> Add first transaction
              </Button>
            </div>
          }
        />
      )}

      {/* P0 Key Figures Section */}
      <section aria-label="Key figures" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {overview.isPending || !ready
          ? TILES.map((t) => (
              <Skeleton key={t.key} className="h-24" aria-label={`Loading ${t.label}`} />
            ))
          : overview.isError
            ? (
              <ErrorState
                className="sm:col-span-2 xl:col-span-5"
                error={overview.error}
                onRetry={() => void overview.refetch()}
              />
            )
            : (
              TILES.map((t) => (
                <KpiTile
                  key={t.key}
                  label={t.label}
                  tile={ov![t.key]}
                  goodWhenUp={t.goodWhenUp}
                  percent={t.percent}
                  previousLabel={ov!.previous_period.label}
                />
              ))
            )}
      </section>

      {/* P1 Planning & Balance Sheet Section */}
      {ov && (
        <section aria-label="Planning and balance sheet" className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">Balance Sheet & Financial Planning</h2>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
            {/* Net Worth Tile */}
            <Card className="hover:border-primary/50 transition-colors">
              <Link to="/net-worth" className="block p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Net Worth</span>
                  <Scale className="size-3.5" />
                </div>
                <p className="mt-1 text-lg font-bold tabular-nums">
                  {ov.net_worth ? money(ov.net_worth.value) : '—'}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground flex items-center gap-0.5">
                  View breakdown <ChevronRight className="size-3" />
                </p>
              </Link>
            </Card>

            {/* Total Assets Tile */}
            <Card className="hover:border-primary/50 transition-colors">
              <Link to="/net-worth" className="block p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Total Assets</span>
                  <TrendingUp className="size-3.5 text-success" />
                </div>
                <p className="mt-1 text-lg font-bold tabular-nums text-success">
                  {ov.total_assets ? money(ov.total_assets.value) : '—'}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Bank, gold, FDs & holdings
                </p>
              </Link>
            </Card>

            {/* Total Liabilities Tile */}
            <Card className="hover:border-primary/50 transition-colors">
              <Link to="/net-worth" className="block p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Total Liabilities</span>
                  <TrendingDown className="size-3.5 text-destructive" />
                </div>
                <p className="mt-1 text-lg font-bold tabular-nums text-destructive">
                  {ov.total_liabilities ? money(ov.total_liabilities.value) : '—'}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Loans, cards & debts
                </p>
              </Link>
            </Card>

            {/* Outstanding Loans Tile */}
            <Card className="hover:border-primary/50 transition-colors">
              <Link to="/loans" className="block p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Outstanding Loans</span>
                  <Landmark className="size-3.5" />
                </div>
                <p className="mt-1 text-lg font-bold tabular-nums text-destructive">
                  {ov.outstanding_loans ? money(ov.outstanding_loans.value) : '—'}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground flex items-center gap-0.5">
                  View loans <ChevronRight className="size-3" />
                </p>
              </Link>
            </Card>

            {/* Monthly EMI Commitment Tile */}
            <Card className="hover:border-primary/50 transition-colors">
              <Link to="/loans" className="block p-4">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span className="text-xs font-medium">Monthly EMI</span>
                  <CreditCard className="size-3.5" />
                </div>
                <p className="mt-1 text-lg font-bold tabular-nums text-primary">
                  {ov.monthly_emi_commitment ? money(ov.monthly_emi_commitment.value) : '—'}
                </p>
                <p className="mt-1 text-[11px] text-muted-foreground">
                  Active monthly obligation
                </p>
              </Link>
            </Card>

            {/* Savings Target Tile */}
            <Card className="hover:border-primary/50 transition-colors">
              {ov.savings_target?.configured ? (
                <Link to="/goals" className="block p-4">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-medium">Savings Target</span>
                    <PiggyBank className="size-3.5 text-primary" />
                  </div>
                  <p className="mt-1 text-lg font-bold tabular-nums">
                    {formatPercent(ov.savings_target.achievement_pct)}
                  </p>
                  <p className="mt-1 text-[11px] text-muted-foreground">
                    {money(ov.savings_target.actual_savings)} of {money(ov.savings_target.target_amount)}
                  </p>
                </Link>
              ) : (
                <div className="p-4 flex flex-col justify-between h-full">
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span className="text-xs font-medium">Savings Target</span>
                    <PiggyBank className="size-3.5" />
                  </div>
                  <div className="py-1">
                    <Link
                      to="/goals"
                      className="text-xs font-semibold text-primary underline underline-offset-4"
                    >
                      Set a target
                    </Link>
                  </div>
                  <p className="text-[11px] text-muted-foreground">Not configured</p>
                </div>
              )}
            </Card>
          </div>
        </section>
      )}

      {/* Budget Status & Active Alerts on Dashboard */}
      {ov && (ov.budget_utilization_pct || (ov.budget_alerts && ov.budget_alerts.length > 0)) && (
        <Card className="border-amber-500/20 bg-amber-500/5">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="size-4 text-amber-500" />
                <CardTitle className="text-sm font-semibold">
                  Budget Status & Spending Alerts
                </CardTitle>
              </div>
              <Link
                to="/budgets"
                className="text-xs text-primary font-medium hover:underline flex items-center"
              >
                Manage Budgets <ChevronRight className="size-3" />
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {ov.budget_utilization_pct && (
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Overall Budget Utilization:</span>
                  <span className="font-semibold tabular-nums">
                    {formatPercent(ov.budget_utilization_pct)}
                  </span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      'h-full transition-all',
                      Number(ov.budget_utilization_pct) > 100
                        ? 'bg-destructive'
                        : Number(ov.budget_utilization_pct) > 80
                          ? 'bg-amber-500'
                          : 'bg-primary',
                    )}
                    style={{
                      width: `${Math.min(100, Math.max(0, Number(ov.budget_utilization_pct)))}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {ov.budget_alerts && ov.budget_alerts.length > 0 && (
              <div className="divide-y rounded-md border bg-background text-xs">
                {ov.budget_alerts.map((alert) => (
                  <div
                    key={alert.category_name}
                    className="flex items-center justify-between p-2.5"
                  >
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={alert.threshold_crossed >= 100 ? 'destructive' : 'outline'}
                        className="text-[10px]"
                      >
                        {alert.threshold_crossed}%
                      </Badge>
                      <span className="font-medium">{alert.category_name}</span>
                    </div>
                    <div className="flex items-center gap-3 tabular-nums text-muted-foreground">
                      <span>
                        Spent {money(alert.spent)} of {money(alert.budgeted)}
                      </span>
                      <strong className={cn(alert.threshold_crossed >= 100 ? 'text-destructive' : 'text-amber-500')}>
                        {formatPercent(alert.utilization_pct)}
                      </strong>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Existing Charts: Income vs Expenses & Savings Trend */}
      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard
          title="Income vs expenses"
          isLoading={trends.isPending}
          error={trends.error}
          onRetry={() => void trends.refetch()}
          isEmpty={trendEmpty}
          emptyAction={<Button size="sm" onClick={() => setAddTxn(true)}>Add transaction</Button>}
          table={<MonthsTable months={months} />}
        >
          <IncomeExpenseChart months={months} />
        </ChartCard>
        <ChartCard
          title="Savings trend"
          isLoading={trends.isPending}
          error={trends.error}
          onRetry={() => void trends.refetch()}
          isEmpty={trendEmpty}
          table={<MonthsTable months={months} />}
        >
          <SavingsTrendChart months={months} />
        </ChartCard>
      </div>

      {/* P1 Planning Trend Charts: Net Worth Growth, Asset Allocation, Loan Trend */}
      {ov && (((ov.net_worth_trend?.length ?? 0) > 0) || ((ov.asset_allocation?.length ?? 0) > 0) || ((ov.loan_trend?.length ?? 0) > 0)) && (
        <div className="grid gap-6 lg:grid-cols-3">
          {/* Net Worth Trend */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">Net Worth Growth</CardTitle>
                <Link to="/net-worth" className="text-xs text-primary hover:underline">
                  View all
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {!ov.net_worth_trend || ov.net_worth_trend.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No snapshots recorded yet
                </div>
              ) : (
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={ov.net_worth_trend}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="as_of" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(val: unknown) => [money(String(val ?? '0')), 'Net Worth']} />
                      <Area
                        type="monotone"
                        dataKey="net_worth"
                        stroke="#3b82f6"
                        fill="#3b82f6"
                        fillOpacity={0.2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Asset Allocation */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">Asset Allocation</CardTitle>
                <Link to="/net-worth" className="text-xs text-primary hover:underline">
                  Details
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {!ov.asset_allocation || ov.asset_allocation.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No assets to allocate
                </div>
              ) : (
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={ov.asset_allocation}
                        dataKey="share_pct"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        innerRadius={35}
                        outerRadius={65}
                        paddingAngle={2}
                      >
                        {ov.asset_allocation.map((_, i) => (
                          <Cell
                            key={i}
                            fill={ALLOCATION_COLORS[i % ALLOCATION_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(val: unknown) => [`${val}%`, 'Share']} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Loan Outstanding Trend */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold">Loan Outstanding Trend</CardTitle>
                <Link to="/loans" className="text-xs text-primary hover:underline">
                  View loans
                </Link>
              </div>
            </CardHeader>
            <CardContent>
              {!ov.loan_trend || ov.loan_trend.length === 0 ? (
                <div className="py-8 text-center text-xs text-muted-foreground">
                  No active loan history
                </div>
              ) : (
                <div className="h-44 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={ov.loan_trend}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} />
                      <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                      <YAxis tick={{ fontSize: 10 }} />
                      <Tooltip formatter={(val: unknown) => [money(String(val ?? '0')), 'Outstanding']} />
                      <Bar dataKey="total_outstanding" fill="#ef4444" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Categories Breakdown & Recent Transactions */}
      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard
          title="Expenses by category"
          isLoading={breakdown.isPending}
          error={breakdown.error}
          onRetry={() => void breakdown.refetch()}
          isEmpty={!breakdown.data?.categories.length}
          emptyTitle="No expenses in this period"
          table={
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Category</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead className="text-right">Share</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {breakdown.data?.categories.map((c) => (
                  <TableRow key={c.name}>
                    <TableCell>{c.name}</TableCell>
                    <TableCell className="text-right tabular-nums">{money(c.total)}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPercent(c.share)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          }
        >
          {breakdown.data && <CategoryDonut rows={breakdown.data.categories} onSelect={drillDown} />}
        </ChartCard>

        <Card>
          <CardContent className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">Recent transactions</h2>
              <Link to="/transactions" className="text-sm text-primary underline underline-offset-4">
                View all
              </Link>
            </div>
            {recent.isPending ? (
              <Skeleton className="h-48" aria-label="Loading recent transactions" />
            ) : recent.isError ? (
              <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />
            ) : recent.data.data.length === 0 ? (
              <EmptyState
                title="No transactions yet"
                action={<Button size="sm" onClick={() => setAddTxn(true)}>Add transaction</Button>}
              />
            ) : (
              <ul className="divide-y" aria-label="Recent transactions">
                {recent.data.data.map((t) => (
                  <li key={t.id} className="flex items-center gap-3 py-2 text-sm">
                    <span className="w-20 shrink-0 text-muted-foreground">{date(t.txn_date)}</span>
                    <span className="min-w-0 flex-1 truncate">
                      {t.description ?? t.payee ?? t.category_name ?? t.type}
                    </span>
                    <span
                      className={cn(
                        'tabular-nums',
                        (t.type === 'income' || t.type === 'refund') && 'text-success',
                      )}
                    >
                      {t.type === 'expense' ? '−' : t.type === 'transfer' ? '' : '+'}
                      {money(t.amount)}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </div>

      <TransactionFormDialog open={addTxn} onOpenChange={setAddTxn} />
      <AccountFormDialog open={addAccount} onOpenChange={setAddAccount} />
    </div>
  )
}
