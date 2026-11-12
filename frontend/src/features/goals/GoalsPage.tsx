import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  Clock,
  Edit2,
  History,
  PiggyBank,
  Plus,
  Target,
  Trash2,
  TrendingUp,
} from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { EmptyState, ErrorState, LoadingBlock, PageHeader } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useFormatters } from '@/features/settings/usePreferences'
import { formatPercent } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { GoalOut } from '@/services/api/types'

import { useDeleteGoal, useGoals, useSavingsTarget } from './api'
import { GoalContributionDialog } from './GoalContributionDialog'
import { GoalContributionsModal } from './GoalContributionsModal'
import { GoalFormDialog } from './GoalFormDialog'
import { SavingsTargetDialog } from './SavingsTargetDialog'

function getCurrentMonth(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  return `${y}-${m}`
}

const TYPE_LABELS: Record<string, string> = {
  emergency_fund: 'Emergency Fund',
  vacation: 'Vacation',
  house: 'House / Real Estate',
  vehicle: 'Vehicle',
  education: 'Education',
  retirement: 'Retirement',
  other: 'Other Goal',
}

export function GoalsPage() {
  const { money, date } = useFormatters()
  const [selectedMonth, setSelectedMonth] = useState<string>(getCurrentMonth)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  const [targetDialogOpen, setTargetDialogOpen] = useState(false)
  const [goalFormOpen, setGoalFormOpen] = useState(false)
  const [selectedGoalForEdit, setSelectedGoalForEdit] = useState<GoalOut | null>(null)
  const [selectedGoalForEntry, setSelectedGoalForEntry] = useState<GoalOut | null>(null)
  const [selectedGoalForHistory, setSelectedGoalForHistory] = useState<GoalOut | null>(null)
  const [goalToDelete, setGoalToDelete] = useState<GoalOut | null>(null)

  const savingsTargetQuery = useSavingsTarget(selectedMonth)
  const goalsQuery = useGoals(statusFilter)
  const deleteGoal = useDeleteGoal()

  const targetData = savingsTargetQuery.data
  const goals = goalsQuery.data ?? []

  const handleDeleteGoal = async () => {
    if (!goalToDelete) return
    try {
      await deleteGoal.mutateAsync(goalToDelete.id)
      toast.success('Goal deleted')
      setGoalToDelete(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete goal'
      toast.error(msg)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Savings & Goals"
        description="Set monthly savings targets and track progress toward your financial milestones."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setTargetDialogOpen(true)}
            >
              <Target className="mr-1.5 size-3.5" />
              {targetData ? 'Update Target' : 'Set Savings Target'}
            </Button>
            <Button
              size="sm"
              onClick={() => {
                setSelectedGoalForEdit(null)
                setGoalFormOpen(true)
              }}
            >
              <Plus className="mr-1.5 size-3.5" />
              New Goal
            </Button>
          </div>
        }
      />

      {/* Monthly Savings Target Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <PiggyBank className="size-5 text-primary" />
              <CardTitle className="text-base font-semibold">
                Monthly Savings Target ({selectedMonth})
              </CardTitle>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="month"
                aria-label="Savings target month"
                className="h-8 rounded-md border bg-background px-2 text-xs font-medium focus:outline-none"
                value={selectedMonth}
                onChange={(e) => e.target.value && setSelectedMonth(e.target.value)}
              />
              <Button
                variant="ghost"
                size="sm"
                className="h-8 text-xs"
                onClick={() => setTargetDialogOpen(true)}
              >
                Change
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {savingsTargetQuery.isPending ? (
            <LoadingBlock label="Loading savings target..." />
          ) : savingsTargetQuery.isError ? (
            <ErrorState
              error={savingsTargetQuery.error}
              onRetry={() => void savingsTargetQuery.refetch()}
            />
          ) : !targetData ? (
            <div className="flex flex-col items-center justify-center p-6 text-center">
              <p className="text-sm text-muted-foreground">
                No savings target configured yet. Setting a monthly savings target helps you stay disciplined.
              </p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={() => setTargetDialogOpen(true)}
              >
                Set a target
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <p className="text-xs text-muted-foreground">Target Amount</p>
                  <p className="text-lg font-semibold tabular-nums">
                    {money(String(targetData.target_amount))}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Actual Savings</p>
                  <p
                    className={cn(
                      'text-lg font-semibold tabular-nums',
                      Number(targetData.actual_savings) < 0 ? 'text-destructive' : 'text-foreground',
                    )}
                  >
                    {money(String(targetData.actual_savings))}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Achievement</p>
                  <div className="flex items-center gap-1.5">
                    <p className="text-lg font-semibold tabular-nums">
                      {formatPercent(String(targetData.achievement_pct))}
                    </p>
                    {targetData.is_achieved && (
                      <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                        Achieved
                      </Badge>
                    )}
                  </div>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Shortfall</p>
                  <p
                    className={cn(
                      'text-lg font-semibold tabular-nums',
                      Number(targetData.shortfall) > 0 ? 'text-destructive' : 'text-success',
                    )}
                  >
                    {money(String(targetData.shortfall))}
                  </p>
                </div>
              </div>

              <div className="space-y-1">
                <div className="h-2.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className={cn(
                      'h-full transition-all',
                      targetData.is_achieved ? 'bg-emerald-500' : 'bg-primary',
                    )}
                    style={{
                      width: `${Math.min(100, Math.max(0, Number(targetData.achievement_pct)))}%`,
                    }}
                    role="progressbar"
                    aria-valuenow={Number(targetData.achievement_pct)}
                    aria-valuemin={0}
                    aria-valuemax={100}
                  />
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Financial Goals Section */}
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold tracking-tight">Financial Goals</h2>
          <Tabs value={statusFilter} onValueChange={setStatusFilter} className="w-auto">
            <TabsList className="h-8">
              <TabsTrigger value="all" className="text-xs">
                All
              </TabsTrigger>
              <TabsTrigger value="active" className="text-xs">
                Active
              </TabsTrigger>
              <TabsTrigger value="paused" className="text-xs">
                Paused
              </TabsTrigger>
              <TabsTrigger value="completed" className="text-xs">
                Completed
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        {goalsQuery.isPending ? (
          <LoadingBlock label="Loading goals..." />
        ) : goalsQuery.isError ? (
          <ErrorState error={goalsQuery.error} onRetry={() => void goalsQuery.refetch()} />
        ) : goals.length === 0 ? (
          <EmptyState
            title="No financial goals yet"
            description="Create named goals for your emergency fund, vacation, house down payment, or retirement."
            action={
              <Button
                onClick={() => {
                  setSelectedGoalForEdit(null)
                  setGoalFormOpen(true)
                }}
              >
                Create your first goal
              </Button>
            }
          />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {goals.map((g) => {
              const progressNum = Math.min(100, Math.max(0, Number(g.progress_pct)))
              return (
                <Card key={g.id} className="flex flex-col justify-between">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="space-y-1">
                        <CardTitle className="text-base font-semibold">{g.name}</CardTitle>
                        <div className="flex flex-wrap items-center gap-1.5">
                          <Badge variant="outline" className="text-[11px]">
                            {TYPE_LABELS[g.type] ?? g.type}
                          </Badge>
                          {g.is_overdue && <Badge variant="destructive">Overdue</Badge>}
                          {g.is_achieved && (
                            <Badge
                              variant="outline"
                              className="border-emerald-500 text-emerald-500"
                            >
                              Achieved
                            </Badge>
                          )}
                          {g.status === 'paused' && <Badge variant="secondary">Paused</Badge>}
                        </div>
                      </div>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-4">
                    {/* Amount & Progress */}
                    <div className="space-y-2">
                      <div className="flex items-baseline justify-between text-sm">
                        <span className="font-semibold tabular-nums">
                          {money(String(g.current_amount))}
                        </span>
                        <span className="text-xs text-muted-foreground tabular-nums">
                          of {money(String(g.target_amount))}
                        </span>
                      </div>

                      <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={cn(
                            'h-full transition-all',
                            g.is_achieved
                              ? 'bg-emerald-500'
                              : g.is_overdue
                                ? 'bg-destructive'
                                : 'bg-primary',
                          )}
                          style={{ width: `${progressNum}%` }}
                          role="progressbar"
                          aria-valuenow={progressNum}
                          aria-valuemin={0}
                          aria-valuemax={100}
                        />
                      </div>

                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{formatPercent(String(g.progress_pct))}</span>
                        <span>Remaining: {money(String(g.remaining_amount))}</span>
                      </div>
                    </div>

                    {/* Projections Card (labeled as estimate) */}
                    <div className="rounded-lg border bg-muted/30 p-2.5 text-xs space-y-1.5">
                      <div className="flex items-center justify-between text-muted-foreground font-medium">
                        <span className="flex items-center gap-1">
                          <TrendingUp className="size-3" />
                          Projections (estimate)
                        </span>
                        {g.target_date && (
                          <span className="flex items-center gap-1">
                            <Calendar className="size-3" />
                            Target: {date(String(g.target_date))}
                          </span>
                        )}
                      </div>

                      {g.is_overdue ? (
                        <p className="flex items-center gap-1 text-destructive font-medium">
                          <AlertCircle className="size-3" />
                          Target date passed — goal is overdue
                        </p>
                      ) : g.is_achieved ? (
                        <p className="flex items-center gap-1 text-success font-medium">
                          <CheckCircle2 className="size-3" />
                          Goal fully funded!
                        </p>
                      ) : (
                        <div className="space-y-1 text-muted-foreground">
                          {g.required_monthly_contribution ? (
                            <p>
                              Required:{' '}
                              <strong className="text-foreground tabular-nums">
                                {money(String(g.required_monthly_contribution))}/mo
                              </strong>{' '}
                              (estimate)
                            </p>
                          ) : null}
                          <p className="flex items-center gap-1">
                            <Clock className="size-3" />
                            ETA:{' '}
                            <span className="text-foreground font-medium">
                              {g.estimated_completion_label}
                            </span>
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>

                  <CardFooter className="flex flex-wrap items-center justify-between gap-2 border-t pt-3">
                    <div className="flex items-center gap-1">
                      <Button
                        size="sm"
                        variant="default"
                        className="h-8 text-xs"
                        onClick={() => setSelectedGoalForEntry(g)}
                        aria-label={`Contribute to ${g.name}`}
                      >
                        Contribute
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 text-xs"
                        onClick={() => setSelectedGoalForHistory(g)}
                        aria-label={`History for ${g.name}`}
                      >
                        <History className="size-3.5 mr-1" />
                        History
                      </Button>
                    </div>

                    <div className="flex items-center gap-1">
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-8"
                        onClick={() => {
                          setSelectedGoalForEdit(g)
                          setGoalFormOpen(true)
                        }}
                        aria-label={`Edit ${g.name}`}
                      >
                        <Edit2 className="size-3.5" />
                      </Button>
                      <Button
                        size="icon"
                        variant="ghost"
                        className="size-8 text-destructive hover:bg-destructive/10"
                        onClick={() => setGoalToDelete(g)}
                        aria-label={`Delete ${g.name}`}
                      >
                        <Trash2 className="size-3.5" />
                      </Button>
                    </div>
                  </CardFooter>
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <SavingsTargetDialog
        open={targetDialogOpen}
        onOpenChange={setTargetDialogOpen}
        currentMonth={selectedMonth}
        currentTargetAmount={targetData?.target_amount}
      />

      <GoalFormDialog
        open={goalFormOpen}
        onOpenChange={setGoalFormOpen}
        goal={selectedGoalForEdit}
      />

      {selectedGoalForEntry && (
        <GoalContributionDialog
          open={Boolean(selectedGoalForEntry)}
          onOpenChange={(open) => !open && setSelectedGoalForEntry(null)}
          goal={selectedGoalForEntry}
        />
      )}

      {selectedGoalForHistory && (
        <GoalContributionsModal
          open={Boolean(selectedGoalForHistory)}
          onOpenChange={(open) => !open && setSelectedGoalForHistory(null)}
          goal={selectedGoalForHistory}
        />
      )}

      <ConfirmDialog
        open={Boolean(goalToDelete)}
        onOpenChange={(open) => !open && setGoalToDelete(null)}
        title={`Delete "${goalToDelete?.name}"?`}
        description="This will permanently delete this goal and all associated contribution records. This action cannot be undone."
        confirmLabel="Delete Goal"
        onConfirm={handleDeleteGoal}
      />
    </div>
  )
}
