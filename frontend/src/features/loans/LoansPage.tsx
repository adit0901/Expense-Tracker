import {
  Calendar,
  Plus,
  Sparkles,
  Trash2,
} from 'lucide-react'
import { useState } from 'react'
import { useParams } from 'react-router'
import { toast } from 'sonner'

import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { EmptyState, ErrorState, LoadingBlock, PageHeader } from '@/components/common/states'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useFormatters } from '@/features/settings/usePreferences'
import { cn } from '@/lib/utils'
import type { LoanOut, LoanType } from '@/services/api/types'

import { useDeleteLoan, useLoans, useLoanSummary } from './api'
import { ConfirmPaymentDialog } from './ConfirmPaymentDialog'
import { LoanFormDialog } from './LoanFormDialog'
import { LoanScheduleModal } from './LoanScheduleModal'
import { PrepaymentDialog } from './PrepaymentDialog'
import { RateChangeDialog } from './RateChangeDialog'
import { SimulationDrawer } from './SimulationDrawer'

const LOAN_TYPE_LABELS: Record<string, string> = {
  home: 'Home Loan',
  car: 'Car Loan',
  personal: 'Personal Loan',
  education: 'Education Loan',
  other: 'Other Loan',
}

export function LoansPage() {
  const { money, date } = useFormatters()
  const params = useParams<{ type?: string }>()

  const initialTab = params.type && params.type in LOAN_TYPE_LABELS ? params.type : 'all'
  const [selectedType, setSelectedType] = useState<string>(initialTab)

  const [addLoanOpen, setAddLoanOpen] = useState(false)
  const [loanForSchedule, setLoanForSchedule] = useState<LoanOut | null>(null)
  const [loanForPayment, setLoanForPayment] = useState<LoanOut | null>(null)
  const [loanForPrepayment, setLoanForPrepayment] = useState<LoanOut | null>(null)
  const [loanForRateChange, setLoanForRateChange] = useState<LoanOut | null>(null)
  const [loanForSimulation, setLoanForSimulation] = useState<LoanOut | null>(null)
  const [loanToDelete, setLoanToDelete] = useState<LoanOut | null>(null)

  const loansQuery = useLoans()
  const summaryQuery = useLoanSummary()
  const deleteLoan = useDeleteLoan()

  const allLoans = loansQuery.data ?? []
  const summary = summaryQuery.data

  const filteredLoans = selectedType === 'all'
    ? allLoans
    : allLoans.filter((l) => l.type === selectedType)

  const handleDelete = async () => {
    if (!loanToDelete) return
    try {
      await deleteLoan.mutateAsync(loanToDelete.id)
      toast.success('Loan deleted')
      setLoanToDelete(null)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to delete loan'
      toast.error(msg)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Loans & EMIs"
        description="Track your active loans, reducing-balance EMIs, amortization schedules, prepayments and repayment simulations."
        actions={
          <Button size="sm" onClick={() => setAddLoanOpen(true)}>
            <Plus className="mr-1.5 size-3.5" />
            Add Loan
          </Button>
        }
      />

      {/* Summary KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Outstanding Principal
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-destructive">
              {summary ? money(String(summary.total_outstanding)) : '—'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Across all active borrowed loans
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Monthly EMI Commitment
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums text-primary">
              {summary ? money(String(summary.total_monthly_emi_commitment)) : '—'}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Total monthly installment obligations
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Active Loans
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold tabular-nums">
              {summary?.active_loans_count ?? 0}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Currently reducing-balance commitments
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filter Tabs by Loan Type */}
      <div className="space-y-4">
        <Tabs value={selectedType} onValueChange={setSelectedType} className="w-full">
          <TabsList className="h-9">
            <TabsTrigger value="all" className="text-xs">
              All Loans
            </TabsTrigger>
            <TabsTrigger value="home" className="text-xs">
              Home Loans
            </TabsTrigger>
            <TabsTrigger value="car" className="text-xs">
              Car Loans
            </TabsTrigger>
            <TabsTrigger value="personal" className="text-xs">
              Personal Loans
            </TabsTrigger>
            <TabsTrigger value="education" className="text-xs">
              Education Loans
            </TabsTrigger>
            <TabsTrigger value="other" className="text-xs">
              Other Loans
            </TabsTrigger>
          </TabsList>
        </Tabs>

        {loansQuery.isPending ? (
          <LoadingBlock label="Loading loans..." />
        ) : loansQuery.isError ? (
          <ErrorState error={loansQuery.error} onRetry={() => void loansQuery.refetch()} />
        ) : filteredLoans.length === 0 ? (
          <EmptyState
            title="No loans found"
            description={
              selectedType === 'all'
                ? 'No active loans recorded. Add your home, car, or personal loans to track repayment schedules and EMIs.'
                : `No ${LOAN_TYPE_LABELS[selectedType] ?? selectedType} loans found.`
            }
            action={<Button onClick={() => setAddLoanOpen(true)}>Add your first loan</Button>}
          />
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {filteredLoans.map((loan) => (
              <Card key={loan.id} className="flex flex-col justify-between">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold">{loan.lender}</CardTitle>
                      <div className="mt-1 flex items-center gap-1.5">
                        <Badge variant="outline" className="text-[11px]">
                          {LOAN_TYPE_LABELS[loan.type] ?? loan.type}
                        </Badge>
                        <Badge
                          variant={loan.status === 'active' ? 'outline' : 'secondary'}
                          className={cn(
                            'text-[11px]',
                            loan.status === 'active' && 'border-emerald-500 text-emerald-500',
                          )}
                        >
                          {loan.status}
                        </Badge>
                        {loan.emi_overridden && (
                          <Badge variant="secondary" className="text-[10px]">
                            Custom EMI
                          </Badge>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-muted-foreground">Monthly EMI</p>
                      <p className="text-lg font-bold tabular-nums text-primary">
                        {money(String(loan.emi_amount))}
                      </p>
                    </div>
                  </div>
                </CardHeader>

                <CardContent className="space-y-4">
                  {/* Key Loan Figures */}
                  <div className="grid grid-cols-2 gap-3 rounded-lg border bg-muted/20 p-3 text-xs">
                    <div>
                      <span className="text-muted-foreground">Outstanding:</span>
                      <p className="font-semibold tabular-nums text-destructive text-sm">
                        {money(String(loan.current_outstanding))}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Original Principal:</span>
                      <p className="font-semibold tabular-nums text-sm">
                        {money(String(loan.original_principal))}
                      </p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Interest Rate:</span>
                      <p className="font-medium tabular-nums">{loan.annual_rate}% p.a.</p>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Remaining Tenure:</span>
                      <p className="font-medium tabular-nums">
                        {loan.remaining_installments} of {loan.tenure_months} months
                      </p>
                    </div>
                  </div>

                  {/* Paid to Date Summary */}
                  <div className="grid grid-cols-2 gap-2 text-xs border-t pt-2 text-muted-foreground">
                    <div>
                      <span>Principal Paid: </span>
                      <strong className="text-foreground tabular-nums">
                        {money(String(loan.paid_principal))}
                      </strong>
                    </div>
                    <div>
                      <span>Interest Paid: </span>
                      <strong className="text-destructive tabular-nums">
                        {money(String(loan.paid_interest))}
                      </strong>
                    </div>
                  </div>

                  {/* Next Due EMI Information */}
                  {loan.next_emi_date && (
                    <div className="flex items-center justify-between rounded-md bg-primary/5 border border-primary/20 px-3 py-2 text-xs">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="size-3.5 text-primary" />
                        <span>
                          Next EMI Due: <strong>{date(String(loan.next_emi_date))}</strong>
                        </span>
                      </div>
                      <Button
                        size="sm"
                        className="h-7 text-xs"
                        onClick={() => setLoanForPayment(loan)}
                      >
                        Confirm EMI
                      </Button>
                    </div>
                  )}
                </CardContent>

                <CardFooter className="flex flex-wrap items-center justify-between gap-1 border-t pt-3">
                  <div className="flex flex-wrap items-center gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs"
                      onClick={() => setLoanForSchedule(loan)}
                    >
                      Schedule
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs"
                      onClick={() => setLoanForPrepayment(loan)}
                    >
                      Prepay
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs"
                      onClick={() => setLoanForRateChange(loan)}
                    >
                      Rate Change
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="h-8 text-xs text-primary"
                      onClick={() => setLoanForSimulation(loan)}
                    >
                      <Sparkles className="mr-1 size-3" />
                      Simulate
                    </Button>
                  </div>

                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-destructive hover:bg-destructive/10"
                    onClick={() => setLoanToDelete(loan)}
                    aria-label={`Delete ${loan.lender}`}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      <LoanFormDialog
        open={addLoanOpen}
        onOpenChange={setAddLoanOpen}
        defaultType={selectedType !== 'all' ? (selectedType as LoanType) : undefined}
      />

      {loanForPayment && (
        <ConfirmPaymentDialog
          open={Boolean(loanForPayment)}
          onOpenChange={(op) => !op && setLoanForPayment(null)}
          loan={loanForPayment}
        />
      )}

      {loanForPrepayment && (
        <PrepaymentDialog
          open={Boolean(loanForPrepayment)}
          onOpenChange={(op) => !op && setLoanForPrepayment(null)}
          loan={loanForPrepayment}
        />
      )}

      {loanForRateChange && (
        <RateChangeDialog
          open={Boolean(loanForRateChange)}
          onOpenChange={(op) => !op && setLoanForRateChange(null)}
          loan={loanForRateChange}
        />
      )}

      {loanForSchedule && (
        <LoanScheduleModal
          open={Boolean(loanForSchedule)}
          onOpenChange={(op) => !op && setLoanForSchedule(null)}
          loan={loanForSchedule}
        />
      )}

      {loanForSimulation && (
        <SimulationDrawer
          open={Boolean(loanForSimulation)}
          onOpenChange={(op) => !op && setLoanForSimulation(null)}
          loan={loanForSimulation}
        />
      )}

      <ConfirmDialog
        open={Boolean(loanToDelete)}
        onOpenChange={(op) => !op && setLoanToDelete(null)}
        title={`Delete "${loanToDelete?.lender}"?`}
        description="This will permanently delete this loan, its payment records and schedule. This action cannot be undone."
        confirmLabel="Delete Loan"
        onConfirm={handleDelete}
      />
    </div>
  )
}
