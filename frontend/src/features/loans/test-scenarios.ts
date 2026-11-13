import type { InstallmentOut, LoanOut, LoanScheduleOut, LoanSummaryOut, LoanType } from '@/services/api/types'

export type BreakUIScenario = 'demo' | 'worst' | 'empty' | 'one' | 'huge'

function makeLoan(partial: Omit<LoanOut, 'updated_at'> & { updated_at?: string }): LoanOut {
  return {
    ...partial,
    updated_at: partial.updated_at ?? '2026-11-01T00:00:00Z',
  }
}

export const DEMO_LOANS: LoanOut[] = [
  makeLoan({
    id: 'demo-loan-1',
    type: 'home',
    lender: 'HDFC Bank Home Loan',
    original_principal: '4500000.00',
    annual_rate: '8.75',
    tenure_months: 240,
    start_date: '2023-05-10',
    first_emi_date: '2023-06-10',
    emi_amount: '39780.00',
    emi_overridden: false,
    baseline_outstanding: '4500000.00',
    baseline_date: '2023-05-10',
    current_outstanding: '4120500.00',
    paid_principal: '379500.00',
    paid_interest: '575220.00',
    remaining_interest: '3755940.00',
    remaining_installments: 198,
    next_emi_date: '2026-12-10',
    next_emi_amount: '39780.00',
    end_date: '2043-05-10',
    status: 'active',
    notes: 'Primary residence home loan linked to repo rate',
    created_at: '2023-05-10T10:00:00Z',
  }),
  makeLoan({
    id: 'demo-loan-2',
    type: 'car',
    lender: 'ICICI Bank Car Loan',
    original_principal: '850000.00',
    annual_rate: '9.20',
    tenure_months: 60,
    start_date: '2024-01-15',
    first_emi_date: '2024-02-15',
    emi_amount: '17730.00',
    emi_overridden: false,
    baseline_outstanding: '850000.00',
    baseline_date: '2024-01-15',
    current_outstanding: '542100.00',
    paid_principal: '307900.00',
    paid_interest: '82160.00',
    remaining_interest: '131640.00',
    remaining_installments: 38,
    next_emi_date: '2026-12-15',
    next_emi_amount: '17730.00',
    end_date: '2029-01-15',
    status: 'active',
    notes: 'Electric vehicle loan auto-debit on 15th',
    created_at: '2024-01-15T12:00:00Z',
  }),
  makeLoan({
    id: 'demo-loan-3',
    type: 'personal',
    lender: 'SBI Xpress Credit',
    original_principal: '300000.00',
    annual_rate: '11.50',
    tenure_months: 36,
    start_date: '2025-01-05',
    first_emi_date: '2025-02-05',
    emi_amount: '9890.00',
    emi_overridden: false,
    baseline_outstanding: '300000.00',
    baseline_date: '2025-01-05',
    current_outstanding: '138400.00',
    paid_principal: '161600.00',
    paid_interest: '36180.00',
    remaining_interest: '10060.00',
    remaining_installments: 15,
    next_emi_date: '2026-12-05',
    next_emi_amount: '9890.00',
    end_date: '2028-01-05',
    status: 'active',
    notes: 'Home renovation instant credit line',
    created_at: '2025-01-05T09:30:00Z',
  }),
]

export const DEMO_SUMMARY: LoanSummaryOut = {
  total_outstanding: '4801000.00',
  total_monthly_emi_commitment: '67400.00',
  active_loans_count: 3,
}

export const WORST_LOANS: LoanOut[] = [
  // Row 1: Extremely long lender name, multi-crore amounts, 360-month tenure, high interest numbers
  makeLoan({
    id: 'worst-1',
    type: 'home',
    lender: 'Housing Development & Infrastructure Finance Corporation of South Asia Bank Limited — Corporate Branch #4920',
    original_principal: '50000000.00',
    annual_rate: '9.45',
    tenure_months: 360,
    start_date: '2025-01-05',
    first_emi_date: '2025-02-05',
    emi_amount: '418890.45',
    emi_overridden: false,
    baseline_outstanding: '50000000.00',
    baseline_date: '2025-01-05',
    current_outstanding: '48976543.21',
    paid_principal: '1023456.79',
    paid_interest: '4567890.12',
    remaining_interest: '101822672.00',
    remaining_installments: 348,
    next_emi_date: '2026-12-05',
    next_emi_amount: '418890.45',
    end_date: '2055-01-05',
    status: 'active',
    notes: 'Consortium mortgage with 30-year amortization schedule and tiered benchmark interest rate',
    created_at: '2025-01-05T00:00:00Z',
  }),
  // Row 2: Unbreakable continuous lender string, 0.00% interest rate, custom EMI badge, exactly 1 remaining installment
  makeLoan({
    id: 'worst-2',
    type: 'car',
    lender: 'StateBankOfHyderabad-RetailAssetsAndAssetReconstructionSecuritizationBranch',
    original_principal: '1200000.00',
    annual_rate: '0.00',
    tenure_months: 36,
    start_date: '2023-12-01',
    first_emi_date: '2024-01-01',
    emi_amount: '33333.33',
    emi_overridden: true,
    baseline_outstanding: '1200000.00',
    baseline_date: '2023-12-01',
    current_outstanding: '33333.33',
    paid_principal: '1166666.67',
    paid_interest: '0.00',
    remaining_interest: '0.00',
    remaining_installments: 1,
    next_emi_date: '2026-11-30',
    next_emi_amount: '33333.33',
    end_date: '2026-12-01',
    status: 'active',
    notes: 'Zero interest subvention promotional car loan',
    created_at: '2023-12-01T00:00:00Z',
  }),
  // Row 3: Accented / Unicode / non-Latin Devanagari script + emoji, high floating rate (24.75%), closed status, missing next_emi_date (null)
  makeLoan({
    id: 'worst-3',
    type: 'education',
    lender: 'भारतीय स्टेट बैंक — 🏦 SBI Global Ed-vantage (मुंबई दक्षिण उपनगर)',
    original_principal: '2500000.00',
    annual_rate: '24.75',
    tenure_months: 84,
    start_date: '2019-06-15',
    first_emi_date: '2019-07-15',
    emi_amount: '61985.00',
    emi_overridden: false,
    baseline_outstanding: '2500000.00',
    baseline_date: '2019-06-15',
    current_outstanding: '0.00',
    paid_principal: '2500000.00',
    paid_interest: '1824900.50',
    remaining_interest: '0.00',
    remaining_installments: 0,
    next_emi_date: null,
    next_emi_amount: null,
    end_date: '2026-06-15',
    status: 'closed',
    notes: 'Overseas master program loan fully amortized and closed',
    created_at: '2019-06-15T00:00:00Z',
  }),
  // Row 4: Two-letter lender name ("Jo"), minimal ₹1.00 amounts, 1-month tenure, 0 paid interest
  makeLoan({
    id: 'worst-4',
    type: 'personal',
    lender: 'Jo',
    original_principal: '1.00',
    annual_rate: '1.00',
    tenure_months: 1,
    start_date: '2026-11-01',
    first_emi_date: '2026-12-01',
    emi_amount: '1.00',
    emi_overridden: false,
    baseline_outstanding: '1.00',
    baseline_date: '2026-11-01',
    current_outstanding: '1.00',
    paid_principal: '0.00',
    paid_interest: '0.00',
    remaining_interest: '0.00',
    remaining_installments: 1,
    next_emi_date: '2026-12-01',
    next_emi_amount: '1.00',
    end_date: '2026-12-01',
    status: 'active',
    notes: 'Micro-test loan record for token loan verification',
    created_at: '2026-11-01T00:00:00Z',
  }),
  // Row 5: Lowercase lender name, irregular decimals and uneven amounts
  makeLoan({
    id: 'worst-5',
    type: 'other',
    lender: 'lic housing finance ltd (consumer credit & mortgage division)',
    original_principal: '9876543.21',
    annual_rate: '13.33',
    tenure_months: 180,
    start_date: '2022-03-10',
    first_emi_date: '2022-04-10',
    emi_amount: '124567.89',
    emi_overridden: true,
    baseline_outstanding: '9876543.21',
    baseline_date: '2022-03-10',
    current_outstanding: '8765432.10',
    paid_principal: '1111111.11',
    paid_interest: '2222222.22',
    remaining_interest: '13656788.10',
    remaining_installments: 145,
    next_emi_date: '2026-12-15',
    next_emi_amount: '124567.89',
    end_date: '2037-03-10',
    status: 'active',
    notes: 'Mortgage against commercial property with floating spread adjustment',
    created_at: '2022-03-10T00:00:00Z',
  }),
]

export const WORST_SUMMARY: LoanSummaryOut = {
  total_outstanding: '57775309.64',
  total_monthly_emi_commitment: '638776.67',
  active_loans_count: 4,
}

export const EMPTY_LOANS: LoanOut[] = []
export const EMPTY_SUMMARY: LoanSummaryOut = {
  total_outstanding: '0.00',
  total_monthly_emi_commitment: '0.00',
  active_loans_count: 0,
}

export const ONE_LOANS: LoanOut[] = [
  makeLoan({
    id: 'one-loan-1',
    type: 'home',
    lender: 'SBI Home Finance',
    original_principal: '3000000.00',
    annual_rate: '8.50',
    tenure_months: 120,
    start_date: '2024-05-10',
    first_emi_date: '2024-06-10',
    emi_amount: '37200.00',
    emi_overridden: false,
    baseline_outstanding: '3000000.00',
    baseline_date: '2024-05-10',
    current_outstanding: '2850000.00',
    paid_principal: '150000.00',
    paid_interest: '85000.00',
    remaining_interest: '1614000.00',
    remaining_installments: 114,
    next_emi_date: '2026-12-10',
    next_emi_amount: '37200.00',
    end_date: '2034-05-10',
    status: 'active',
    notes: 'Sole active home loan',
    created_at: '2024-05-10T10:00:00Z',
  }),
]

export const ONE_SUMMARY: LoanSummaryOut = {
  total_outstanding: '2850000.00',
  total_monthly_emi_commitment: '37200.00',
  active_loans_count: 1,
}

let cachedHugeLoans: LoanOut[] | null = null
let cachedHugeSummary: LoanSummaryOut | null = null

export function getHugeLoans(): LoanOut[] {
  if (cachedHugeLoans) return cachedHugeLoans

  const types: LoanType[] = ['home', 'car', 'personal', 'education', 'other']
  const lenders = [
    'Axis Bank Priority Loan',
    'Kotak Mahindra Prime Finance',
    'Bank of Baroda Retail Hub',
    'Punjab National Bank Corporate Credit',
    'Tata Capital Financial Services',
    'Bajaj Housing Finance Ltd',
    'Federal Bank Personal Lines',
    'Canara Bank Fast-Track Mortgage',
  ]

  const loans: LoanOut[] = []
  let totalOutstanding = 0
  let totalEmi = 0

  for (let i = 1; i <= 1000; i++) {
    const loanType = types[i % types.length] ?? 'personal'
    const lender = `${lenders[i % lenders.length]} #${i}`
    const principal = 100000 + ((i * 17923) % 4500000)
    const rate = (7.5 + ((i * 1.37) % 8.5)).toFixed(2)
    const tenure = 12 + ((i * 6) % 240)
    const emi = Math.round(principal / (tenure || 1) + (principal * parseFloat(rate)) / 1200)
    const currentOutstanding = Math.max(0, principal - emi * (i % 5))
    const remaining = Math.max(1, tenure - (i % 5))

    totalOutstanding += currentOutstanding
    totalEmi += emi

    loans.push(
      makeLoan({
        id: `huge-loan-${i}`,
        type: loanType,
        lender,
        original_principal: principal.toFixed(2),
        annual_rate: rate,
        tenure_months: tenure,
        start_date: '2024-01-01',
        first_emi_date: '2024-02-01',
        emi_amount: emi.toFixed(2),
        emi_overridden: i % 7 === 0,
        baseline_outstanding: principal.toFixed(2),
        baseline_date: '2024-01-01',
        current_outstanding: currentOutstanding.toFixed(2),
        paid_principal: (principal - currentOutstanding).toFixed(2),
        paid_interest: ((principal * 0.08 * (i % 5)) / 12).toFixed(2),
        remaining_interest: ((currentOutstanding * parseFloat(rate) * (remaining / 12)) / 100).toFixed(2),
        remaining_installments: remaining,
        next_emi_date: i % 15 === 0 ? null : '2026-12-05',
        next_emi_amount: i % 15 === 0 ? null : emi.toFixed(2),
        end_date: '2030-01-01',
        status: i % 20 === 0 ? 'closed' : 'active',
        notes: `Batch test record #${i}`,
        created_at: '2024-01-01T00:00:00Z',
      }),
    )
  }

  cachedHugeLoans = loans
  cachedHugeSummary = {
    total_outstanding: totalOutstanding.toFixed(2),
    total_monthly_emi_commitment: totalEmi.toFixed(2),
    active_loans_count: loans.filter((l) => l.status === 'active').length,
  }

  return loans
}

export function getHugeSummary(): LoanSummaryOut {
  if (!cachedHugeSummary) {
    getHugeLoans()
  }
  return cachedHugeSummary!
}

export function getScenarioLoans(scenario: BreakUIScenario, status?: string): LoanOut[] {
  let list: LoanOut[] = []
  switch (scenario) {
    case 'demo':
      list = DEMO_LOANS
      break
    case 'worst':
      list = WORST_LOANS
      break
    case 'empty':
      list = EMPTY_LOANS
      break
    case 'one':
      list = ONE_LOANS
      break
    case 'huge':
      list = getHugeLoans()
      break
  }
  if (status && status !== 'all') {
    return list.filter((l) => l.status === status)
  }
  return list
}

export function getScenarioSummary(scenario: BreakUIScenario): LoanSummaryOut {
  switch (scenario) {
    case 'demo':
      return DEMO_SUMMARY
    case 'worst':
      return WORST_SUMMARY
    case 'empty':
      return EMPTY_SUMMARY
    case 'one':
      return ONE_SUMMARY
    case 'huge':
      return getHugeSummary()
  }
}

export function getScenarioLoan(id: string, scenario: BreakUIScenario): LoanOut | undefined {
  const loans = getScenarioLoans(scenario)
  return loans.find((l) => l.id === id)
}

export function getScenarioSchedule(id: string, scenario: BreakUIScenario): LoanScheduleOut {
  const loan: LoanOut = getScenarioLoan(id, scenario) ?? WORST_LOANS[0]!

  const tenure = Math.min(loan.tenure_months, 360)
  const installments: InstallmentOut[] = []
  const emiNum = parseFloat(loan.emi_amount)
  let balance = parseFloat(loan.original_principal)
  const monthlyRate = parseFloat(loan.annual_rate) / 12 / 100

  for (let i = 1; i <= tenure; i++) {
    const interest = balance * monthlyRate
    const principal = Math.min(balance, Math.max(0, emiNum - interest))
    balance = Math.max(0, balance - principal)
    const isPaid = i <= (loan.tenure_months - loan.remaining_installments)

    const year = 2025 + Math.floor((i - 1) / 12)
    const month = String(((i - 1) % 12) + 1).padStart(2, '0')

    installments.push({
      installment_no: i,
      due_date: `${year}-${month}-05`,
      payment: emiNum.toFixed(2),
      principal: principal.toFixed(2),
      interest: interest.toFixed(2),
      closing_outstanding: balance.toFixed(2),
      is_paid: isPaid,
      paid_date: isPaid ? `${year}-${month}-05` : null,
    })
  }

  const totalInterest = installments.reduce((acc, inst) => acc + parseFloat(inst.interest), 0)

  return {
    loan_id: loan.id,
    total_principal: loan.original_principal,
    total_interest: totalInterest.toFixed(2),
    emi: loan.emi_amount,
    end_date: installments[installments.length - 1]?.due_date ?? null,
    installments,
  }
}
