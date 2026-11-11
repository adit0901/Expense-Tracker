import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight, Plus } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router'

import { CategoryDonut } from '@/components/charts/CategoryDonut'
import { ChartCard } from '@/components/charts/ChartCard'
import { IncomeExpenseChart, MonthsTable, SavingsTrendChart } from '@/components/charts/TrendCharts'
import { EmptyState, ErrorState, PageHeader } from '@/components/common/states'
import { PeriodFilter } from '@/components/common/PeriodFilter'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { AccountFormDialog } from '@/features/accounts/AccountFormDialog'
import { useFormatters } from '@/features/settings/usePreferences'
import { TransactionFormDialog } from '@/features/transactions/TransactionFormDialog'
import { type TxnPage } from '@/features/transactions/api'
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

function KpiTile({ label, tile, goodWhenUp, percent, previousLabel }: {
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
        <p className="mt-1 text-xl font-semibold tabular-nums">{percent ? formatPercent(tile.value) : money(tile.value)}</p>
        <p className={cn('mt-1 flex items-center gap-1 text-xs', good && 'text-success', bad && 'text-destructive', !good && !bad && 'text-muted-foreground')}>
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
    const p = new URLSearchParams({ category_id: row.category_id, date_from: ov.period.start, date_to: ov.period.end })
    p.append('type', 'expense')
    navigate(`/transactions?${p.toString()}`)
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Overview" description={ov ? ov.period.label : undefined} actions={<PeriodFilter />} />

      {isNewUser && (
        <EmptyState
          title="Welcome to FinTrack"
          description={ov.has_accounts
            ? 'Add your first income or expense to see your dashboard come alive.'
            : 'Start by adding an account (bank, cash, card or wallet), then record your first transaction.'}
          action={
            <div className="flex flex-wrap justify-center gap-2">
              {!ov.has_accounts && <Button onClick={() => setAddAccount(true)}><Plus aria-hidden /> Add account</Button>}
              <Button variant={ov.has_accounts ? 'default' : 'outline'} onClick={() => setAddTxn(true)}><Plus aria-hidden /> Add first transaction</Button>
            </div>
          }
        />
      )}

      <section aria-label="Key figures" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {overview.isPending || !ready
          ? TILES.map((t) => <Skeleton key={t.key} className="h-24" aria-label={`Loading ${t.label}`} />)
          : overview.isError
            ? <ErrorState className="sm:col-span-2 xl:col-span-5" error={overview.error} onRetry={() => void overview.refetch()} />
            : TILES.map((t) => (
              <KpiTile key={t.key} label={t.label} tile={ov![t.key]} goodWhenUp={t.goodWhenUp} percent={t.percent}
                previousLabel={ov!.previous_period.label} />
            ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard title="Income vs expenses" isLoading={trends.isPending} error={trends.error}
          onRetry={() => void trends.refetch()} isEmpty={trendEmpty}
          emptyAction={<Button size="sm" onClick={() => setAddTxn(true)}>Add transaction</Button>}
          table={<MonthsTable months={months} />}>
          <IncomeExpenseChart months={months} />
        </ChartCard>
        <ChartCard title="Savings trend" isLoading={trends.isPending} error={trends.error}
          onRetry={() => void trends.refetch()} isEmpty={trendEmpty}
          table={<MonthsTable months={months} />}>
          <SavingsTrendChart months={months} />
        </ChartCard>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <ChartCard title="Expenses by category" isLoading={breakdown.isPending} error={breakdown.error}
          onRetry={() => void breakdown.refetch()} isEmpty={!breakdown.data?.categories.length}
          emptyTitle="No expenses in this period"
          table={
            <Table>
              <TableHeader><TableRow><TableHead>Category</TableHead><TableHead className="text-right">Amount</TableHead><TableHead className="text-right">Share</TableHead></TableRow></TableHeader>
              <TableBody>
                {breakdown.data?.categories.map((c) => (
                  <TableRow key={c.name}><TableCell>{c.name}</TableCell><TableCell className="text-right tabular-nums">{money(c.total)}</TableCell>
                    <TableCell className="text-right tabular-nums">{formatPercent(c.share)}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          }>
          {breakdown.data && <CategoryDonut rows={breakdown.data.categories} onSelect={drillDown} />}
        </ChartCard>

        <Card>
          <CardContent className="p-4">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-base font-semibold">Recent transactions</h2>
              <Link to="/transactions" className="text-sm text-primary underline underline-offset-4">View all</Link>
            </div>
            {recent.isPending ? (
              <Skeleton className="h-48" aria-label="Loading recent transactions" />
            ) : recent.isError ? (
              <ErrorState error={recent.error} onRetry={() => void recent.refetch()} />
            ) : recent.data.data.length === 0 ? (
              <EmptyState title="No transactions yet" action={<Button size="sm" onClick={() => setAddTxn(true)}>Add transaction</Button>} />
            ) : (
              <ul className="divide-y" aria-label="Recent transactions">
                {recent.data.data.map((t) => (
                  <li key={t.id} className="flex items-center gap-3 py-2 text-sm">
                    <span className="w-20 shrink-0 text-muted-foreground">{date(t.txn_date)}</span>
                    <span className="min-w-0 flex-1 truncate">{t.description ?? t.payee ?? t.category_name ?? t.type}</span>
                    <span className={cn('tabular-nums', (t.type === 'income' || t.type === 'refund') && 'text-success')}>
                      {t.type === 'expense' ? '−' : t.type === 'transfer' ? '' : '+'}{money(t.amount)}
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
