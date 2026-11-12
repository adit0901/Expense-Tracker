import {
  AlertCircle,
  ArrowDownRight,
  ArrowUpRight,
  Camera,
  History,
  Plus,
  RefreshCw,
} from 'lucide-react'
import { useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { toast } from 'sonner'

import { ErrorState, LoadingBlock, PageHeader } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useFormatters } from '@/features/settings/usePreferences'
import { formatPercent } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { AssetOut, LiabilityOut } from '@/services/api/types'

import {
  useAssets,
  useLiabilities,
  useNetWorth,
  useNetWorthSnapshots,
  useRecomputeSnapshot,
  useTakeSnapshot,
} from './api'
import { AssetFormDialog } from './AssetFormDialog'
import { BalanceHistoryModal } from './BalanceHistoryModal'
import { LiabilityFormDialog } from './LiabilityFormDialog'
import { ValuationHistoryModal } from './ValuationHistoryModal'

const CHART_COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald
  '#f59e0b', // amber
  '#8b5cf6', // purple
  '#ec4899', // pink
  '#06b6d4', // cyan
  '#f97316', // orange
  '#64748b', // slate
]

export function NetWorthPage() {
  const { money, date } = useFormatters()
  const [includeClosed, setIncludeClosed] = useState(false)
  const [assetFormOpen, setAssetFormOpen] = useState(false)
  const [liabilityFormOpen, setLiabilityFormOpen] = useState(false)
  const [selectedAsset, setSelectedAsset] = useState<AssetOut | null>(null)
  const [selectedLiability, setSelectedLiability] = useState<LiabilityOut | null>(null)

  const netWorthQuery = useNetWorth()
  const snapshotsQuery = useNetWorthSnapshots()
  const assetsQuery = useAssets(includeClosed)
  const liabilitiesQuery = useLiabilities(includeClosed)

  const recompute = useRecomputeSnapshot()
  const takeSnapshot = useTakeSnapshot()

  const nw = netWorthQuery.data
  const snapshots = snapshotsQuery.data ?? []
  const assets = assetsQuery.data ?? []
  const liabilities = liabilitiesQuery.data ?? []

  const handleRecompute = async () => {
    if (!nw) return
    try {
      await recompute.mutateAsync(String(nw.as_of))
      toast.success('Net worth recomputed')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to recompute'
      toast.error(msg)
    }
  }

  const handleTakeSnapshot = async () => {
    try {
      await takeSnapshot.mutateAsync()
      toast.success('Snapshot created')
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to take snapshot'
      toast.error(msg)
    }
  }

  const momChange = nw?.mom_growth?.amount_change
  const momPct = nw?.mom_growth?.percentage_change
  const yoyChange = nw?.yoy_growth?.amount_change
  const yoyPct = nw?.yoy_growth?.percentage_change

  const momUp = momChange !== null && momChange !== undefined && Number(momChange) > 0
  const momDown = momChange !== null && momChange !== undefined && Number(momChange) < 0

  return (
    <div className="space-y-6">
      <PageHeader
        title="Net Worth"
        description="Your total financial position: assets minus liabilities across bank accounts, investments, properties, and loans."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleTakeSnapshot}
              disabled={takeSnapshot.isPending}
            >
              <Camera className="mr-1.5 size-3.5" />
              Take Snapshot
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setLiabilityFormOpen(true)}
            >
              <Plus className="mr-1.5 size-3.5" />
              Add Liability
            </Button>
            <Button
              size="sm"
              onClick={() => setAssetFormOpen(true)}
            >
              <Plus className="mr-1.5 size-3.5" />
              Add Asset
            </Button>
          </div>
        }
      />

      {/* KPI Cards: Net Worth, Assets, Liabilities */}
      {netWorthQuery.isPending ? (
        <LoadingBlock label="Calculating net worth..." />
      ) : netWorthQuery.isError ? (
        <ErrorState error={netWorthQuery.error} onRetry={() => void netWorthQuery.refetch()} />
      ) : (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card className="border-primary/20">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  Net Worth
                </CardTitle>
                <div className="flex items-center gap-1.5">
                  {nw?.is_stale && (
                    <Badge
                      variant="outline"
                      className="border-amber-500 bg-amber-500/10 text-amber-500 gap-1 text-[11px]"
                    >
                      <AlertCircle className="size-3" />
                      Outdated
                    </Badge>
                  )}
                  {nw?.is_stale && (
                    <Button
                      variant="ghost"
                      size="icon"
                      className="size-6 text-amber-500"
                      aria-label="Recompute net worth"
                      onClick={handleRecompute}
                      disabled={recompute.isPending}
                    >
                      <RefreshCw className={cn('size-3', recompute.isPending && 'animate-spin')} />
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-2xl font-bold tabular-nums">
                {money(String(nw?.net_worth ?? '0.00'))}
              </p>
              <div className="space-y-1 text-xs text-muted-foreground">
                <div className="flex items-center gap-1">
                  <span>MoM:</span>
                  {momPct !== null && momPct !== undefined ? (
                    <span
                      className={cn(
                        'flex items-center font-medium tabular-nums',
                        momUp && 'text-emerald-500',
                        momDown && 'text-destructive',
                      )}
                    >
                      {momUp && <ArrowUpRight className="size-3" />}
                      {momDown && <ArrowDownRight className="size-3" />}
                      {money(String(momChange))} ({formatPercent(String(momPct), { signed: true })})
                    </span>
                  ) : (
                    <span>—</span>
                  )}
                </div>
                <div className="flex items-center gap-1">
                  <span>YoY:</span>
                  {yoyPct !== null && yoyPct !== undefined ? (
                    <span className="font-medium tabular-nums">
                      {money(String(yoyChange))} ({formatPercent(String(yoyPct), { signed: true })})
                    </span>
                  ) : (
                    <span>—</span>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Assets
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-2xl font-bold tabular-nums text-success">
                {money(String(nw?.total_assets ?? '0.00'))}
              </p>
              <p className="text-xs text-muted-foreground">
                Liquid Assets:{' '}
                <strong className="text-foreground tabular-nums">
                  {money(String(nw?.liquid_assets ?? '0.00'))}
                </strong>
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                Total Liabilities
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-2xl font-bold tabular-nums text-destructive">
                {money(String(nw?.total_liabilities ?? '0.00'))}
              </p>
              <p className="text-xs text-muted-foreground">
                Includes credit cards, active loans, overdrafts and debts
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Asset Allocation & Snapshot History Charts */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Asset Breakdown Chart */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-semibold">Asset Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            {!nw?.asset_breakdown || nw.asset_breakdown.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                No asset records available to show allocation.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                <div className="h-52 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={nw.asset_breakdown}
                        dataKey="share_pct"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={2}
                      >
                        {nw.asset_breakdown.map((_, idx) => (
                          <Cell
                            key={idx}
                            fill={CHART_COLORS[idx % CHART_COLORS.length]}
                          />
                        ))}
                      </Pie>
                      <Tooltip
                        formatter={(val: unknown) => [`${val}%`, 'Share']}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>

                <div className="space-y-2 text-xs">
                  {nw.asset_breakdown.map((item, idx) => (
                    <div key={item.category} className="flex items-center justify-between">
                      <div className="flex items-center gap-2 truncate">
                        <span
                          className="size-2.5 rounded-full shrink-0"
                          style={{ backgroundColor: CHART_COLORS[idx % CHART_COLORS.length] }}
                        />
                        <span className="truncate">{item.category}</span>
                      </div>
                      <div className="text-right shrink-0 font-medium tabular-nums pl-2">
                        <span>{formatPercent(String(item.share_pct))}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Net Worth Snapshot Trend Chart */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Net Worth Trend</CardTitle>
              <span className="text-xs text-muted-foreground">
                {snapshots.length} snapshots recorded
              </span>
            </div>
          </CardHeader>
          <CardContent>
            {snapshots.length === 0 ? (
              <div className="py-12 text-center text-sm text-muted-foreground">
                No snapshots taken yet. Automatic month-end snapshots will populate this chart.
              </div>
            ) : (
              <div className="h-52 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={snapshots}>
                    <defs>
                      <linearGradient id="nwGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="as_of" />
                    <YAxis />
                    <Tooltip
                      formatter={(val: unknown) => [money(String(val ?? '0')), 'Net Worth']}
                    />
                    <Area
                      type="monotone"
                      dataKey="net_worth"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#nwGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Assets & Liabilities Tables */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold tracking-tight">Manual Assets & Liabilities</h3>
          <div className="flex items-center space-x-2">
            <Checkbox
              id="show-closed"
              checked={includeClosed}
              onCheckedChange={(checked) => setIncludeClosed(Boolean(checked))}
            />
            <label htmlFor="show-closed" className="text-xs text-muted-foreground cursor-pointer">
              Show closed items
            </label>
          </div>
        </div>

        {/* Assets Section */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Assets</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setAssetFormOpen(true)}>
                <Plus className="mr-1 size-3.5" />
                Add Asset
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {assetsQuery.isPending ? (
              <LoadingBlock label="Loading assets..." />
            ) : assets.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                No manual assets recorded. Add your fixed deposits, gold, properties, or retirement schemes.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Asset Name</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead className="text-right">Current Value</TableHead>
                    <TableHead>As of Date</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {assets.map((a) => (
                    <TableRow key={a.id}>
                      <TableCell className="font-medium">{a.name}</TableCell>
                      <TableCell className="capitalize text-xs text-muted-foreground">
                        {a.type.replace(/_/g, ' ')}
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums text-success">
                        {money(String(a.current_value))}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {a.latest_valuation_date ? date(String(a.latest_valuation_date)) : '—'}
                      </TableCell>
                      <TableCell className="text-center">
                        {a.closed_at ? (
                          <Badge variant="secondary">Closed</Badge>
                        ) : a.is_liquid ? (
                          <Badge variant="outline" className="border-blue-500 text-blue-500">
                            Liquid
                          </Badge>
                        ) : (
                          <Badge variant="outline">Active</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-xs"
                          onClick={() => setSelectedAsset(a)}
                          aria-label={`Valuation history for ${a.name}`}
                        >
                          <History className="mr-1 size-3" />
                          History
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Liabilities Section */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base font-semibold">Other Liabilities</CardTitle>
              <Button size="sm" variant="outline" onClick={() => setLiabilityFormOpen(true)}>
                <Plus className="mr-1 size-3.5" />
                Add Liability
              </Button>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {liabilitiesQuery.isPending ? (
              <LoadingBlock label="Loading liabilities..." />
            ) : liabilities.length === 0 ? (
              <div className="p-6 text-center text-sm text-muted-foreground">
                No manual debts or family borrowings recorded.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Liability Name</TableHead>
                    <TableHead>Notes</TableHead>
                    <TableHead className="text-right">Outstanding Balance</TableHead>
                    <TableHead>As of Date</TableHead>
                    <TableHead className="text-center">Status</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {liabilities.map((l) => (
                    <TableRow key={l.id}>
                      <TableCell className="font-medium">{l.name}</TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate max-w-[150px]">
                        {l.notes ?? '—'}
                      </TableCell>
                      <TableCell className="text-right font-semibold tabular-nums text-destructive">
                        {money(String(l.current_balance))}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {l.latest_balance_date ? date(String(l.latest_balance_date)) : '—'}
                      </TableCell>
                      <TableCell className="text-center">
                        {l.closed_at ? (
                          <Badge variant="secondary">Closed</Badge>
                        ) : (
                          <Badge variant="outline">Active</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 text-xs"
                          onClick={() => setSelectedLiability(l)}
                          aria-label={`Balance history for ${l.name}`}
                        >
                          <History className="mr-1 size-3" />
                          History
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      <AssetFormDialog open={assetFormOpen} onOpenChange={setAssetFormOpen} />
      <LiabilityFormDialog open={liabilityFormOpen} onOpenChange={setLiabilityFormOpen} />

      {selectedAsset && (
        <ValuationHistoryModal
          open={Boolean(selectedAsset)}
          onOpenChange={(open) => !open && setSelectedAsset(null)}
          asset={selectedAsset}
        />
      )}

      {selectedLiability && (
        <BalanceHistoryModal
          open={Boolean(selectedLiability)}
          onOpenChange={(open) => !open && setSelectedLiability(null)}
          liability={selectedLiability}
        />
      )}
    </div>
  )
}
