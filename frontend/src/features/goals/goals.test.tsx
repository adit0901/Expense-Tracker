import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { expect, test } from 'vitest'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

const mockSavingsTarget = {
  id: 'st-1',
  month: '2026-11',
  effective_from: '2026-11-01',
  target_amount: '30000.00',
  actual_savings: '36000.00',
  achievement_pct: '120.00',
  shortfall: '0.00',
  is_achieved: true,
}

const mockGoals = [
  {
    id: 'g-1',
    name: 'Emergency Fund',
    type: 'emergency_fund',
    target_amount: '300000.00',
    target_date: '2027-08-31',
    starting_amount: '50000.00',
    status: 'active',
    notes: '6 months expenses',
    current_amount: '75000.00',
    progress_pct: '25.00',
    remaining_amount: '225000.00',
    required_monthly_contribution: '25000.00',
    estimated_completion_date: '2027-08-31',
    estimated_completion_label: 'Aug 2027 (estimate)',
    is_overdue: false,
    is_achieved: false,
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
  },
  {
    id: 'g-2',
    name: 'Vacation to Japan',
    type: 'vacation',
    target_amount: '150000.00',
    target_date: '2026-10-31',
    starting_amount: '20000.00',
    status: 'active',
    notes: null,
    current_amount: '20000.00',
    progress_pct: '13.33',
    remaining_amount: '130000.00',
    required_monthly_contribution: null,
    estimated_completion_date: null,
    estimated_completion_label: 'Cannot estimate',
    is_overdue: true,
    is_achieved: false,
    created_at: '2026-09-01T00:00:00Z',
    updated_at: '2026-09-01T00:00:00Z',
  },
]

function setupGoalHandlers() {
  server.use(
    http.get(`${API}/savings-targets`, () =>
      HttpResponse.json({ data: mockSavingsTarget, meta: {} }),
    ),
    http.get(`${API}/goals`, () =>
      HttpResponse.json({ data: mockGoals, meta: {} }),
    ),
  )
}

test('renders savings target vs actual and achievement status', async () => {
  setupGoalHandlers()
  renderApp('/goals')

  expect(await screen.findByRole('heading', { name: 'Savings & Goals' })).toBeInTheDocument()
  expect(await screen.findByText('₹30,000.00')).toBeInTheDocument()
  expect(screen.getAllByText(/Monthly Savings Target/i).length).toBeGreaterThan(0)
  expect(screen.getByText('₹36,000.00')).toBeInTheDocument()
  expect(screen.getByText('120.00%')).toBeInTheDocument()
  expect(screen.getAllByText('Achieved').length).toBeGreaterThan(0)
})

test('renders goal cards with estimate projection labels and overdue state', async () => {
  setupGoalHandlers()
  renderApp('/goals')

  // Emergency Fund goal
  await screen.findByRole('heading', { name: 'Savings & Goals' })
  expect((await screen.findAllByText('Emergency Fund')).length).toBeGreaterThan(0)
  expect(screen.getAllByText(/Projections \(estimate\)/i).length).toBeGreaterThan(0)
  expect(screen.getByText(/₹25,000.00\/mo/i)).toBeInTheDocument()
  expect(screen.getByText(/Aug 2027 \(estimate\)/i)).toBeInTheDocument()

  // Overdue goal with "Cannot estimate"
  expect(screen.getByText('Vacation to Japan')).toBeInTheDocument()
  expect(screen.getByText('Overdue')).toBeInTheDocument()
  expect(screen.getByText(/Target date passed — goal is overdue/i)).toBeInTheDocument()
})

test('allows contributing to a goal', async () => {
  let postBody: Record<string, unknown> | null = null
  setupGoalHandlers()
  server.use(
    http.post(`${API}/goals/:id/contributions`, async ({ request }) => {
      postBody = (await request.json()) as Record<string, unknown>
      return HttpResponse.json({
        data: {
          id: 'c-1',
          goal_id: 'g-1',
          kind: 'contribution',
          amount: postBody.amount,
          date: postBody.date,
          transaction_id: null,
          notes: postBody.notes,
          created_at: new Date().toISOString(),
        },
        meta: {},
      }, { status: 201 })
    }),
  )

  const user = userEvent.setup()
  renderApp('/goals')

  const contributeBtn = await screen.findByRole('button', { name: 'Contribute to Emergency Fund' })
  await user.click(contributeBtn)

  const dialog = await screen.findByRole('dialog')
  const amountInput = within(dialog).getByLabelText(/Amount/i)
  await user.clear(amountInput)
  await user.type(amountInput, '15000.00')

  const confirmBtn = within(dialog).getByRole('button', { name: 'Confirm' })
  await user.click(confirmBtn)

  await waitFor(() => {
    expect(postBody).toMatchObject({
      amount: '15000.00',
    })
  })
})
