import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import type { ExpenseReport, IncomeReport } from '@/services/api/types'
import { API, requests, server } from '@/test/server'
import { renderApp } from '@/test/utils'

const PERIOD = { start: '2026-10-01', end: '2026-10-31', label: 'Oct 2026', granularity: 'month' }

const EXPENSES: ExpenseReport = {
  period: PERIOD,
  total_expenses: '1350.00',
  by_category: [
    { category_id: 'cat-food', name: 'Food', color: null, total: '850.00', share: '62.96', subcategories: [
      { category_id: 'cat-groceries', name: 'Groceries', color: null, total: '50.00', share: '3.70' }] },
    { category_id: 'cat-ent', name: 'Entertainment', color: null, total: '500.00', share: '37.04', subcategories: [] },
  ],
  by_payment_method: [
    { method: 'upi', total: '100.00', share: '7.41' }, { method: 'cash', total: '200.00', share: '14.81' },
    { method: 'debit_card', total: '300.00', share: '22.22' }, { method: 'credit_card', total: '250.00', share: '18.52' },
    { method: 'bank_transfer', total: '500.00', share: '37.04' }, { method: 'other', total: '0.00', share: '0.00' },
  ],
}

const INCOME: IncomeReport = {
  period: { start: '2026-01-01', end: '2026-12-31', label: '2026', granularity: 'year' },
  total_income: '409000.00',
  months: [{ month: '2026-01', label: 'Jan 2026', income: '123000.00' }],
  by_source: [{ source_id: 's1', name: 'Acme Corp Salary', type: 'salary', total: '369000.00', share: '90.22' },
    { source_id: 's2', name: 'Freelance Design', type: 'freelance', total: '40000.00', share: '9.78' }],
  by_category: [{ category_id: 'cat-salary', name: 'Salary', color: null, total: '409000.00', share: '100.00' }],
  salary: { gross: '450000.00', total_deductions: '81000.00', net: '369000.00',
    deductions: [{ name: 'Income Tax/TDS', amount: '75000.00' }],
    months: [{ month: '2026-01', label: 'Jan 2026', gross: '150000.00', total_deductions: '27000.00', net: '123000.00' }] },
}

beforeEach(() => {
  server.use(
    http.get(`${API}/reports/expenses`, () => HttpResponse.json({ data: EXPENSES, meta: {} })),
    http.get(`${API}/reports/income`, () => HttpResponse.json({ data: INCOME, meta: {} })),
    http.get(`${API}/reports/savings-trend`, () => HttpResponse.json({ data: { period: PERIOD, months: [
      { month: '2026-10', label: 'Oct 2026', income: '0.00', expenses: '1350.00', savings: '-1350.00', savings_rate: null }] }, meta: {} })),
  )
})

test('expenses page shows category (with subcategories) and payment-method totals', async () => {
  renderApp('/expenses?period=last_month')
  const methods = await screen.findByRole('table', { name: 'Expenses by payment method' })
  for (const [label, value] of [['UPI', '₹100.00'], ['Cash', '₹200.00'], ['Debit card', '₹300.00'],
    ['Credit card', '₹250.00'], ['Bank transfer', '₹500.00']]) {
    const r = within(methods).getByRole('row', { name: new RegExp(`^${label}`) })
    expect(r).toHaveTextContent(value!)
  }
  expect(within(methods).getByRole('row', { name: /^Total/ })).toHaveTextContent('₹1,350.00')
  expect(screen.getByText('Groceries')).toBeInTheDocument()
  expect(screen.getByRole('link', { name: 'Food' })).toHaveAttribute('href', expect.stringContaining('category_id=cat-food'))
  const q = requests.find((r) => r.path === '/reports/expenses')!
  expect(q.search).toContain('period=last_month')
})

test('income page shows sources and salary gross/deductions/net', async () => {
  renderApp('/income')
  expect(await screen.findByText('Acme Corp Salary')).toBeInTheDocument()
  expect(screen.getByText('Freelance Design')).toBeInTheDocument()
  const total = screen.getByRole('row', { name: /^Total/ })
  expect(total).toHaveTextContent('₹4,09,000.00')
  expect(total).toHaveTextContent('₹4,50,000.00')
  expect(total).toHaveTextContent('₹81,000.00')
  expect(screen.getByText(/Deductions are not counted as expenses/)).toBeInTheDocument()
  expect(requests.find((r) => r.path === '/reports/income')!.search).toContain('period=this_year')
})

test('reports page exports CSV for the selected period and shows N/A rate', async () => {
  let exported = ''
  server.use(http.get(`${API}/reports/savings-trend/export.csv`, ({ request }) => {
    exported = new URL(request.url).search
    return new HttpResponse('month\n', { headers: { 'Content-Type': 'text/csv' } })
  }))
  URL.createObjectURL = vi.fn(() => 'blob:x')
  URL.revokeObjectURL = vi.fn()
  const user = userEvent.setup()
  renderApp('/reports?period=custom&start=2026-07-15&end=2026-09-15')
  await user.click(await screen.findByRole('tab', { name: 'Savings rate' }))
  await user.click((await screen.findAllByRole('button', { name: 'Show table' }))[0]!)
  expect(await screen.findByText('N/A')).toBeInTheDocument()
  await user.click(screen.getByRole('button', { name: /export csv/i }))
  await waitFor(() => expect(exported).toContain('start=2026-07-15'))
  expect(exported).toContain('end=2026-09-15')
})
