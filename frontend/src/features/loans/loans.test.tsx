import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { expect, test } from 'vitest'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

const mockSummary = {
  total_outstanding: '921151.21',
  total_monthly_emi_commitment: '88848.79',
  active_loans_count: 1,
}

const mockLoan = {
  id: 'loan-1',
  type: 'home',
  lender: 'HDFC Home Loan',
  original_principal: '1000000.00',
  annual_rate: '12.00',
  tenure_months: 12,
  start_date: '2026-11-01',
  first_emi_date: '2026-12-01',
  emi_amount: '88848.79',
  emi_overridden: false,
  baseline_outstanding: '1000000.00',
  baseline_date: '2026-11-01',
  current_outstanding: '1000000.00',
  paid_principal: '0.00',
  paid_interest: '0.00',
  remaining_interest: '66185.45',
  remaining_installments: 12,
  next_emi_date: '2026-12-01',
  next_emi_amount: '88848.79',
  end_date: '2027-11-01',
  status: 'active',
  notes: null,
  created_at: '2026-11-01T00:00:00Z',
  updated_at: '2026-11-01T00:00:00Z',
}

const mockSchedule = {
  loan_id: 'loan-1',
  total_principal: '1000000.00',
  total_interest: '66185.45',
  emi: '88848.79',
  end_date: '2027-11-01',
  installments: [
    {
      installment_no: 1,
      due_date: '2026-12-01',
      payment: '88848.79',
      principal: '78848.79',
      interest: '10000.00',
      closing_outstanding: '921151.21',
      is_paid: false,
      paid_date: null,
    },
  ],
}

function setupLoanHandlers() {
  server.use(
    http.get(`${API}/loans`, () =>
      HttpResponse.json({ data: [mockLoan], meta: {} }),
    ),
    http.get(`${API}/loans/summary`, () =>
      HttpResponse.json({ data: mockSummary, meta: {} }),
    ),
    http.get(`${API}/loans/:id/schedule`, () =>
      HttpResponse.json({ data: mockSchedule, meta: {} }),
    ),
  )
}

test('renders loan list and monthly commitment summary', async () => {
  setupLoanHandlers()
  renderApp('/loans')

  expect(await screen.findByRole('heading', { name: 'Loans & EMIs' })).toBeInTheDocument()
  expect(await screen.findByText('HDFC Home Loan')).toBeInTheDocument()
  expect(screen.getAllByText('₹88,848.79').length).toBeGreaterThan(0)
  expect(screen.getByText('₹9,21,151.21')).toBeInTheDocument()
})

test('confirm payment dialog shows split between principal and interest', async () => {
  setupLoanHandlers()
  const user = userEvent.setup()
  renderApp('/loans')

  const scheduleBtn = await screen.findByRole('button', { name: 'Schedule' })
  await user.click(scheduleBtn)

  const scheduleDialog = await screen.findByRole('dialog')
  expect(within(scheduleDialog).getByText(/Amortization Schedule: HDFC Home Loan/i)).toBeInTheDocument()

  const payBtn = within(scheduleDialog).getByRole('button', { name: 'Pay' })
  await user.click(payBtn)

  const confirmDialog = await screen.findByRole('dialog')
  expect(within(confirmDialog).getByText(/Confirm EMI Payment: HDFC Home Loan/i)).toBeInTheDocument()
  expect(within(confirmDialog).getByText('Principal Component (Reduces Liability):')).toBeInTheDocument()
  expect(within(confirmDialog).getByText('₹78,848.79')).toBeInTheDocument()
  expect(within(confirmDialog).getByText('Interest Component (Expense):')).toBeInTheDocument()
  expect(within(confirmDialog).getByText('₹10,000.00')).toBeInTheDocument()
})

test('simulation drawer runs simulation and displays interest saved without saving', async () => {
  setupLoanHandlers()
  let simulated = false
  server.use(
    http.post(`${API}/loans/:id/simulate`, async () => {
      simulated = true
      return HttpResponse.json({
        data: {
          current_total_interest: '66185.45',
          current_emi: '88848.79',
          current_tenure_months: 12,
          current_end_date: '2027-11-01',
          simulated_total_interest: '35000.00',
          simulated_emi: '88848.79',
          simulated_tenure_months: 8,
          simulated_end_date: '2027-07-01',
          interest_saved: '31185.45',
          tenure_months_saved: 4,
        },
        meta: {},
      })
    }),
  )

  const user = userEvent.setup()
  renderApp('/loans')

  const simBtn = await screen.findByRole('button', { name: 'Simulate' })
  await user.click(simBtn)

  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByText(/Loan Repayment Simulation: HDFC Home Loan/i)).toBeInTheDocument()

  const amountInput = within(dialog).getByLabelText(/Lump-Sum Amount/i)
  await user.clear(amountInput)
  await user.type(amountInput, '300000.00')

  const calcBtn = within(dialog).getByRole('button', { name: 'Calculate Simulation' })
  await user.click(calcBtn)

  await waitFor(() => {
    expect(simulated).toBe(true)
  })

  expect(await within(dialog).findByText(/Interest Saved: ₹31,185.45/i)).toBeInTheDocument()
  expect(within(dialog).getByText(/Simulation Results/i)).toBeInTheDocument()
})
