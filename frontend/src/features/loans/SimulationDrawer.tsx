import { Sparkles, TrendingDown } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useFormatters } from '@/features/settings/usePreferences'
import type { LoanOut, LoanSimulateOut } from '@/services/api/types'

import { useSimulateLoan } from './api'

interface SimulationDrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  loan: LoanOut
}

type SimKind = 'one_time_prepayment' | 'extra_monthly_payment' | 'rate_change'

export function SimulationDrawer({ open, onOpenChange, loan }: SimulationDrawerProps) {
  const { money, date } = useFormatters()
  const simulate = useSimulateLoan(loan.id)

  const [kind, setKind] = useState<SimKind>('one_time_prepayment')
  const [amount, setAmount] = useState('')
  const [annualRate, setAnnualRate] = useState('')
  const [strategy, setStrategy] = useState<'reduce_tenure' | 'reduce_emi' | 'keep_emi' | 'keep_tenure'>('reduce_tenure')
  const [effectiveDate, setEffectiveDate] = useState(() => new Date().toISOString().slice(0, 10))

  const [simResult, setSimResult] = useState<LoanSimulateOut | null>(null)

  const handleRunSimulation = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await simulate.mutateAsync({
        kind,
        effective_date: effectiveDate,
        amount: amount ? amount : undefined,
        annual_rate: annualRate ? annualRate : undefined,
        strategy,
      })
      setSimResult(res)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Simulation failed'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <div className="flex items-center gap-2">
            <Sparkles className="size-5 text-primary" />
            <DialogTitle>Loan Repayment Simulation: {loan.lender}</DialogTitle>
          </div>
          <DialogDescription>
            Simulate prepayment or rate change scenarios to see potential interest savings and tenure reductions. Simulations never modify your actual loan.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleRunSimulation} className="space-y-4 py-3">
          <div className="grid grid-cols-3 gap-2">
            <Button
              type="button"
              variant={kind === 'one_time_prepayment' ? 'default' : 'outline'}
              size="sm"
              className="text-xs"
              onClick={() => {
                setKind('one_time_prepayment')
                setStrategy('reduce_tenure')
              }}
            >
              One-Time Prepay
            </Button>
            <Button
              type="button"
              variant={kind === 'extra_monthly_payment' ? 'default' : 'outline'}
              size="sm"
              className="text-xs"
              onClick={() => {
                setKind('extra_monthly_payment')
                setStrategy('reduce_tenure')
              }}
            >
              Extra Monthly EMI
            </Button>
            <Button
              type="button"
              variant={kind === 'rate_change' ? 'default' : 'outline'}
              size="sm"
              className="text-xs"
              onClick={() => {
                setKind('rate_change')
                setStrategy('keep_emi')
              }}
            >
              Rate Change
            </Button>
          </div>

          <div className="grid grid-cols-2 gap-3">
            {kind !== 'rate_change' ? (
              <div className="space-y-1.5">
                <Label htmlFor="sim-amount" className="text-xs">
                  {kind === 'one_time_prepayment' ? 'Lump-Sum Amount (₹)' : 'Extra Monthly Amount (₹)'}
                </Label>
                <Input
                  id="sim-amount"
                  type="number"
                  step="0.01"
                  min="1"
                  placeholder={kind === 'one_time_prepayment' ? '500000.00' : '5000.00'}
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  required
                />
              </div>
            ) : (
              <div className="space-y-1.5">
                <Label htmlFor="sim-rate" className="text-xs">
                  New Rate (% p.a.)
                </Label>
                <Input
                  id="sim-rate"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="8.00"
                  value={annualRate}
                  onChange={(e) => setAnnualRate(e.target.value)}
                  required
                />
              </div>
            )}

            <div className="space-y-1.5">
              <Label htmlFor="sim-date" className="text-xs">
                Effective Date
              </Label>
              <Input
                id="sim-date"
                type="date"
                value={effectiveDate}
                onChange={(e) => setEffectiveDate(e.target.value)}
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="sim-strategy" className="text-xs">
              Strategy
            </Label>
            <select
              id="sim-strategy"
              className="h-8 w-full rounded-md border bg-background px-2 text-xs"
              value={strategy}
              onChange={(e) =>
                setStrategy(e.target.value as 'reduce_tenure' | 'reduce_emi' | 'keep_emi' | 'keep_tenure')
              }
            >
              {kind !== 'rate_change' ? (
                <>
                  <option value="reduce_tenure">Reduce tenure (Keep EMI constant)</option>
                  <option value="reduce_emi">Reduce EMI (Keep remaining tenure)</option>
                </>
              ) : (
                <>
                  <option value="keep_emi">Keep EMI constant (Adjust tenure)</option>
                  <option value="keep_tenure">Keep tenure constant (Adjust EMI)</option>
                </>
              )}
            </select>
          </div>

          <Button type="submit" size="sm" className="w-full" disabled={simulate.isPending}>
            {simulate.isPending ? 'Simulating...' : 'Calculate Simulation'}
          </Button>
        </form>

        {simResult && (
          <div className="rounded-lg border bg-muted/20 p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-sm font-semibold text-success">
                <TrendingDown className="size-4" />
                <span>Simulation Results</span>
              </div>
              <Badge variant="outline" className="border-emerald-500 text-emerald-500">
                Interest Saved: {money(String(simResult.interest_saved))}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-4 text-xs">
              {/* Current Plan */}
              <div className="space-y-2 rounded-md border bg-background p-3">
                <p className="font-semibold text-muted-foreground uppercase text-[11px]">
                  Current Repayment Plan
                </p>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>Monthly EMI:</span>
                    <strong className="tabular-nums">{money(String(simResult.current_emi))}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>Remaining Months:</span>
                    <strong className="tabular-nums">{simResult.current_tenure_months} mo</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>End Date:</span>
                    <strong className="tabular-nums">
                      {simResult.current_end_date ? date(String(simResult.current_end_date)) : '—'}
                    </strong>
                  </div>
                  <div className="flex justify-between border-t pt-1">
                    <span>Total Interest:</span>
                    <strong className="tabular-nums text-destructive">
                      {money(String(simResult.current_total_interest))}
                    </strong>
                  </div>
                </div>
              </div>

              {/* Simulated Plan */}
              <div className="space-y-2 rounded-md border border-primary/30 bg-primary/5 p-3">
                <p className="font-semibold text-primary uppercase text-[11px]">
                  Simulated Plan
                </p>
                <div className="space-y-1">
                  <div className="flex justify-between">
                    <span>New EMI:</span>
                    <strong className="tabular-nums text-primary">{money(String(simResult.simulated_emi))}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span>New Tenure:</span>
                    <strong className="tabular-nums">
                      {simResult.simulated_tenure_months} mo
                      {simResult.tenure_months_saved > 0 && (
                        <span className="text-emerald-500 ml-1">
                          (−{simResult.tenure_months_saved} mo)
                        </span>
                      )}
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span>New End Date:</span>
                    <strong className="tabular-nums">
                      {simResult.simulated_end_date ? date(String(simResult.simulated_end_date)) : '—'}
                    </strong>
                  </div>
                  <div className="flex justify-between border-t pt-1">
                    <span>Total Interest:</span>
                    <strong className="tabular-nums text-success">
                      {money(String(simResult.simulated_total_interest))}
                    </strong>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

