import { useEffect, useMemo, useState } from 'react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useFormatters } from '@/features/settings/usePreferences'
import type { LoanCreate, LoanType } from '@/services/api/types'

import { useCreateLoan } from './api'
import { useBreakUIScenario } from './useBreakUIScenario'

interface LoanFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  defaultType?: LoanType
}

const LOAN_TYPES: { value: LoanType; label: string }[] = [
  { value: 'home', label: 'Home Loan' },
  { value: 'car', label: 'Car Loan' },
  { value: 'personal', label: 'Personal Loan' },
  { value: 'education', label: 'Education Loan' },
  { value: 'other', label: 'Other Loan' },
]

export function computeEmiPreview(principalStr: string, rateStr: string, tenureStr: string): string | null {
  const p = parseFloat(principalStr)
  const rAnnual = parseFloat(rateStr)
  const n = parseInt(tenureStr, 10)

  if (isNaN(p) || isNaN(rAnnual) || isNaN(n) || p <= 0 || rAnnual < 0 || n <= 0) {
    return null
  }

  if (rAnnual === 0) {
    return (p / n).toFixed(2)
  }

  const rMonthly = rAnnual / 12 / 100
  const factor = Math.pow(1 + rMonthly, n)
  const emi = (p * rMonthly * factor) / (factor - 1)
  return emi.toFixed(2)
}

export function LoanFormDialog({ open, onOpenChange, defaultType }: LoanFormDialogProps) {
  const { money } = useFormatters()
  const createLoan = useCreateLoan()

  const [type, setType] = useState<LoanType>(defaultType ?? 'home')
  const [lender, setLender] = useState('')
  const [principal, setPrincipal] = useState('')
  const [annualRate, setAnnualRate] = useState('')
  const [tenureMonths, setTenureMonths] = useState('')
  const [startDate, setStartDate] = useState(() => new Date().toISOString().slice(0, 10))
  const [firstEmiDate, setFirstEmiDate] = useState('')

  // Optional mid-tenure baseline
  const [isMidTenure, setIsMidTenure] = useState(false)
  const [baselineOutstanding, setBaselineOutstanding] = useState('')
  const [baselineDate, setBaselineDate] = useState(() => new Date().toISOString().slice(0, 10))

  // Optional EMI override
  const [overrideEmi, setOverrideEmi] = useState(false)
  const [customEmi, setCustomEmi] = useState('')

  const [notes, setNotes] = useState('')
  const scenario = useBreakUIScenario()

  const applyPreset = (preset: 'demo' | 'worst' | 'zero_rate' | 'unicode' | 'clear') => {
    switch (preset) {
      case 'demo':
        setType('home')
        setLender('HDFC Bank Home Loan')
        setPrincipal('4500000.00')
        setAnnualRate('8.75')
        setTenureMonths('240')
        setStartDate('2023-05-10')
        setFirstEmiDate('2023-06-10')
        setIsMidTenure(false)
        setBaselineOutstanding('')
        setOverrideEmi(false)
        setCustomEmi('')
        setNotes('Primary residence loan linked to repo rate')
        break
      case 'worst':
        setType('home')
        setLender(
          'Housing Development & Infrastructure Finance Corporation of South Asia Bank Limited — Corporate Branch #4920',
        )
        setPrincipal('50000000.00')
        setAnnualRate('9.45')
        setTenureMonths('360')
        setStartDate('2025-01-05')
        setFirstEmiDate('2025-02-05')
        setIsMidTenure(true)
        setBaselineOutstanding('48976543.21')
        setBaselineDate('2025-01-05')
        setOverrideEmi(true)
        setCustomEmi('418890.45')
        setNotes(
          'Consortium mortgage with 30-year amortization schedule and tiered benchmark interest rate',
        )
        break
      case 'zero_rate':
        setType('car')
        setLender('StateBankOfHyderabad-RetailAssetsAndAssetReconstructionSecuritizationBranch')
        setPrincipal('1200000.00')
        setAnnualRate('0.00')
        setTenureMonths('36')
        setStartDate('2024-01-01')
        setFirstEmiDate('2024-02-01')
        setIsMidTenure(false)
        setBaselineOutstanding('')
        setOverrideEmi(true)
        setCustomEmi('33333.33')
        setNotes('Zero interest promotional car loan')
        break
      case 'unicode':
        setType('education')
        setLender('भारतीय स्टेट बैंक — 🏦 SBI Global Ed-vantage (मुंबई दक्षिण उपनगर)')
        setPrincipal('2500000.00')
        setAnnualRate('24.75')
        setTenureMonths('84')
        setStartDate('2024-06-15')
        setFirstEmiDate('2024-07-15')
        setIsMidTenure(false)
        setBaselineOutstanding('')
        setOverrideEmi(false)
        setCustomEmi('')
        setNotes('Higher education overseas degree loan')
        break
      case 'clear':
        setType(defaultType ?? 'home')
        setLender('')
        setPrincipal('')
        setAnnualRate('')
        setTenureMonths('')
        setStartDate(new Date().toISOString().slice(0, 10))
        setFirstEmiDate('')
        setIsMidTenure(false)
        setBaselineOutstanding('')
        setOverrideEmi(false)
        setCustomEmi('')
        setNotes('')
        break
    }
  }

  useEffect(() => {
    if (open) {
      if (scenario === 'worst') {
        applyPreset('worst')
      } else if (scenario === 'demo') {
        applyPreset('demo')
      } else if (defaultType) {
        setType(defaultType)
      }
    }
  }, [open, scenario, defaultType])

  const calculatedEmi = useMemo(() => {
    return computeEmiPreview(principal, annualRate, tenureMonths)
  }, [principal, annualRate, tenureMonths])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const payload: LoanCreate = {
        type,
        lender: lender.trim(),
        original_principal: principal,
        annual_rate: annualRate,
        tenure_months: parseInt(tenureMonths, 10),
        start_date: startDate,
        first_emi_date: firstEmiDate || null,
        emi_amount: overrideEmi && customEmi ? customEmi : null,
        baseline_outstanding: isMidTenure && baselineOutstanding ? baselineOutstanding : null,
        baseline_date: isMidTenure && baselineDate ? baselineDate : null,
        notes: notes.trim() || null,
      }
      await createLoan.mutateAsync(payload)
      toast.success('Loan created successfully')
      onOpenChange(false)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create loan'
      toast.error(msg)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-xl">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Add New Loan</DialogTitle>
            <DialogDescription>
              Configure reducing-balance EMI, amortization schedule, and tracking.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {import.meta.env.DEV && (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-dashed border-primary/40 bg-primary/5 p-2.5 text-xs">
                <div className="flex items-center gap-1.5 font-medium text-primary">
                  <span className="inline-block size-2 rounded-full bg-primary" />
                  <span>Break UI Presets:</span>
                </div>
                <div className="flex flex-wrap items-center gap-1">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[11px]"
                    onClick={() => applyPreset('demo')}
                  >
                    Demo
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[11px]"
                    onClick={() => applyPreset('worst')}
                  >
                    Worst Case
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[11px]"
                    onClick={() => applyPreset('zero_rate')}
                  >
                    0% Rate
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="h-6 px-2 text-[11px]"
                    onClick={() => applyPreset('unicode')}
                  >
                    Unicode
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-[11px] text-muted-foreground hover:text-foreground"
                    onClick={() => applyPreset('clear')}
                  >
                    Clear
                  </Button>
                </div>
              </div>
            )}

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="loan-type">Loan Type</Label>
                <select
                  id="loan-type"
                  className="h-9 w-full rounded-md border bg-background px-3 py-1 text-sm shadow-xs focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                  value={type}
                  onChange={(e) => setType(e.target.value as LoanType)}
                >
                  {LOAN_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="loan-lender">Lender / Bank</Label>
                <Input
                  id="loan-lender"
                  placeholder="e.g. HDFC Bank, SBI"
                  value={lender}
                  onChange={(e) => setLender(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="loan-principal">Principal (₹)</Label>
                <Input
                  id="loan-principal"
                  type="number"
                  step="0.01"
                  min="1"
                  placeholder="5000000.00"
                  value={principal}
                  onChange={(e) => setPrincipal(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="loan-rate">Interest Rate (% p.a.)</Label>
                <Input
                  id="loan-rate"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="8.50"
                  value={annualRate}
                  onChange={(e) => setAnnualRate(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="loan-tenure">Tenure (Months)</Label>
                <Input
                  id="loan-tenure"
                  type="number"
                  step="1"
                  min="1"
                  placeholder="240"
                  value={tenureMonths}
                  onChange={(e) => setTenureMonths(e.target.value)}
                  required
                />
              </div>
            </div>

            {/* Real-time Computed EMI Banner */}
            <div className="rounded-lg border bg-muted/40 p-3 flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground font-medium">
                  Computed Monthly EMI Preview
                </p>
                <p className="text-xl font-bold tabular-nums text-primary">
                  {calculatedEmi ? money(calculatedEmi) : '—'}
                </p>
              </div>
              <div className="text-right text-xs text-muted-foreground">
                <p>Standard reducing balance</p>
                <p>Half-up 2 decimal precision</p>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="loan-start-date">Disbursal / Start Date</Label>
                <Input
                  id="loan-start-date"
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="loan-first-emi">First EMI Date (Optional)</Label>
                <Input
                  id="loan-first-emi"
                  type="date"
                  value={firstEmiDate}
                  onChange={(e) => setFirstEmiDate(e.target.value)}
                />
              </div>
            </div>

            {/* EMI Override */}
            <div className="space-y-2 pt-1 border-t">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="override-emi"
                  checked={overrideEmi}
                  onCheckedChange={(checked) => setOverrideEmi(Boolean(checked))}
                />
                <Label htmlFor="override-emi" className="text-xs font-normal">
                  Override computed EMI to match lender statement
                </Label>
              </div>
              {overrideEmi && (
                <div className="pl-6 space-y-1">
                  <Input
                    type="number"
                    step="0.01"
                    min="1"
                    placeholder="Exact EMI from bank"
                    value={customEmi}
                    onChange={(e) => setCustomEmi(e.target.value)}
                    required={overrideEmi}
                  />
                </div>
              )}
            </div>

            {/* Mid-tenure baseline */}
            <div className="space-y-2 pt-1 border-t">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="mid-tenure"
                  checked={isMidTenure}
                  onCheckedChange={(checked) => setIsMidTenure(Boolean(checked))}
                />
                <Label htmlFor="mid-tenure" className="text-xs font-normal">
                  Existing loan in progress (specify current outstanding principal)
                </Label>
              </div>
              {isMidTenure && (
                <div className="grid grid-cols-2 gap-3 pl-6">
                  <div className="space-y-1">
                    <Label htmlFor="baseline-outstanding" className="text-xs">
                      Outstanding Principal (₹)
                    </Label>
                    <Input
                      id="baseline-outstanding"
                      type="number"
                      step="0.01"
                      min="0"
                      placeholder="380000.00"
                      value={baselineOutstanding}
                      onChange={(e) => setBaselineOutstanding(e.target.value)}
                      required={isMidTenure}
                    />
                  </div>
                  <div className="space-y-1">
                    <Label htmlFor="baseline-date" className="text-xs">
                      As of Date
                    </Label>
                    <Input
                      id="baseline-date"
                      type="date"
                      value={baselineDate}
                      onChange={(e) => setBaselineDate(e.target.value)}
                      required={isMidTenure}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="space-y-1.5 pt-1 border-t">
              <Label htmlFor="loan-notes">Notes (Optional)</Label>
              <Input
                id="loan-notes"
                placeholder="Loan account number, branch, or remarks..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={createLoan.isPending}>
              {createLoan.isPending ? 'Adding...' : 'Create Loan'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

