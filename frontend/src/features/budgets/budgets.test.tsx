import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { expect, test } from 'vitest'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

const mockBudget = {
  id: 'b-1',
  month: '2026-11',
  overall_amount: '60000.00',
  overall_actual: '45000.00',
  overall_utilization: '75.00',
  overall_remaining: '15000.00',
  overall_is_over_budget: false,
  lines: [
    {
      id: 'bl-1',
      category_id: 'cat-food',
      category_name: 'Food',
      amount: '12000.00',
      alert_thresholds: [80, 100],
      actual: '9000.00',
      utilization: '75.00',
      remaining: '3000.00',
      is_over_budget: false,
    },
    {
      id: 'bl-2',
      category_id: 'cat-rent',
      category_name: 'Rent',
      amount: '25000.00',
      alert_thresholds: [80, 100],
      actual: '28000.00',
      utilization: '112.00',
      remaining: '-3000.00',
      is_over_budget: true,
    },
  ],
  warning: null,
}

const mockComparison = {
  category_id: null,
  category_name: null,
  months: [
    {
      month: '2026-10',
      month_label: 'Oct 2026',
      budget: '60000.00',
      actual: '55000.00',
      utilization: '91.67',
      remaining: '5000.00',
      is_over_budget: false,
    },
    {
      month: '2026-11',
      month_label: 'Nov 2026',
      budget: '60000.00',
      actual: '45000.00',
      utilization: '75.00',
      remaining: '15000.00',
      is_over_budget: false,
    },
    {
      month: '2026-12',
      month_label: 'Dec 2026',
      budget: null,
      actual: '10000.00',
      utilization: null,
      remaining: null,
      is_over_budget: false,
    },
  ],
}

const mockAlerts = [
  {
    id: 'ba-1',
    month: '2026-11',
    budget_line_id: 'bl-2',
    category_id: 'cat-rent',
    category_name: 'Rent',
    threshold: 100,
    triggered_at: '2026-11-10T14:30:00Z',
  },
]

function setupBudgetHandlers(budgetOverrides: Record<string, unknown> = {}) {
  server.use(
    http.get(`${API}/budgets`, ({ request }) => {
      const url = new URL(request.url)
      const m = url.searchParams.get('month')
      if (m === '2026-12') {
        return HttpResponse.json({
          data: {
            id: 'b-empty',
            month: '2026-12',
            overall_amount: null,
            overall_actual: '0.00',
            overall_utilization: null,
            overall_remaining: null,
            overall_is_over_budget: false,
            lines: [],
            warning: null,
          },
          meta: {},
        })
      }
      return HttpResponse.json({
        data: { ...mockBudget, ...budgetOverrides },
        meta: {},
      })
    }),
    http.get(`${API}/budgets/comparison`, () =>
      HttpResponse.json({ data: mockComparison, meta: {} }),
    ),
    http.get(`${API}/budget-alerts`, () =>
      HttpResponse.json({ data: mockAlerts, meta: {} }),
    ),
  )
}

test('renders overall budget, category lines, utilization and alerts', async () => {
  setupBudgetHandlers()
  renderApp('/budgets')

  expect(await screen.findByRole('heading', { name: 'Budgets' })).toBeInTheDocument()
  expect(await screen.findByText('Overall Budget')).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'Food' })).toBeInTheDocument()
  expect(screen.getByRole('cell', { name: 'Rent' })).toBeInTheDocument()
  expect(screen.getByText('Over budget')).toBeInTheDocument()
  expect(screen.getByText('Active Spending Alerts')).toBeInTheDocument()
  expect(screen.getByText(/crossed 100% threshold/i)).toBeInTheDocument()
  expect(screen.getByText('Budget vs Actual Comparison')).toBeInTheDocument()
  expect(screen.getAllByText('No budget').length).toBeGreaterThan(0)
})

test('shows warning when category budgets exceed overall budget', async () => {
  setupBudgetHandlers({
    warning: 'Category budgets sum to 70000.00 against a 60000.00 overall budget',
  })
  renderApp('/budgets')

  const warning = await screen.findByRole('alert')
  expect(warning).toHaveTextContent(/Category budgets sum to 70000.00/i)
})

test('allows editing and saving a budget', async () => {
  let putBody: Record<string, unknown> | null = null
  setupBudgetHandlers()
  server.use(
    http.put(`${API}/budgets/:month`, async ({ request }) => {
      putBody = (await request.json()) as Record<string, unknown>
      return HttpResponse.json({
        data: {
          ...mockBudget,
          overall_amount: putBody.overall_amount,
        },
        meta: {},
      })
    }),
  )

  const user = userEvent.setup()
  renderApp('/budgets')

  const editBtn = await screen.findByRole('button', { name: /edit budget/i })
  await user.click(editBtn)

  const dialog = await screen.findByRole('dialog')
  const overallInput = within(dialog).getByLabelText('Overall Monthly Budget')
  await user.clear(overallInput)
  await user.type(overallInput, '65000.00')

  const saveBtn = within(dialog).getByRole('button', { name: 'Save Budget' })
  await user.click(saveBtn)

  await waitFor(() => {
    expect(putBody).toMatchObject({
      overall_amount: '65000.00',
    })
  })
})

test('allows copying forward from another month', async () => {
  let copyCall = ''
  setupBudgetHandlers()
  server.use(
    http.post(`${API}/budgets/:target/copy-from/:source`, ({ params }) => {
      copyCall = `${params.source} -> ${params.target}`
      return HttpResponse.json({ data: mockBudget, meta: {} })
    }),
  )

  const user = userEvent.setup()
  renderApp('/budgets')

  const copyBtn = await screen.findByRole('button', { name: /copy forward/i })
  await user.click(copyBtn)

  const dialog = await screen.findByRole('dialog')
  const sourceInput = within(dialog).getByLabelText('Source Month')
  await user.clear(sourceInput)
  await user.type(sourceInput, '2026-10')

  const submitBtn = within(dialog).getByRole('button', { name: 'Copy Budgets' })
  await user.click(submitBtn)

  await waitFor(() => {
    expect(copyCall).toBe('2026-10 -> 2026-11')
  })
})
