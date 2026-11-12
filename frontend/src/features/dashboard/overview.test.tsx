import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { overview } from '@/test/fixtures'
import { API, db, server } from '@/test/server'
import { renderApp } from '@/test/utils'

test('KPI tiles show values and changes, with a dash for a zero base', async () => {
  renderApp('/')
  const tiles = await screen.findByRole('region', { name: 'Key figures' })
  await within(tiles).findByText('Total income')
  expect(within(tiles).getAllByText('₹1,20,000.00', { selector: 'p' })).toHaveLength(2) // income + liquid funds
  expect(within(tiles).getByText('+20.00%')).toBeInTheDocument()
  expect(within(tiles).getByText('-15.00 pts')).toBeInTheDocument()
  expect(within(tiles).getByText('—')).toBeInTheDocument() // liquid funds previous was 0
  expect(within(tiles).getAllByText('vs Oct 2026').length).toBe(5)
})

test('new user sees an invitation to add an account and first transaction', async () => {
  db.transactions = []
  server.use(http.get(`${API}/dashboard/overview`, () => HttpResponse.json({
    data: overview({ has_transactions: false, has_accounts: false }), meta: {} })))
  renderApp('/')
  expect(await screen.findByText('Welcome to FinTrack')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /add account/i })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: /add first transaction/i })).toBeInTheDocument()
})

test('category drill-down opens Transactions filtered to that category and period', async () => {
  const user = userEvent.setup()
  const { router } = renderApp('/')
  const food = await screen.findByRole('button', { name: /View transactions for Food/ })
  expect(screen.getByRole('button', { name: /Other categories/ })).toBeDisabled()
  await user.click(food)
  await waitFor(() => expect(router.state.location.pathname).toBe('/transactions'))
  const p = new URLSearchParams(router.state.location.search)
  expect(p.get('category_id')).toBe('cat-food')
  expect(p.get('date_from')).toBe('2026-11-01')
  expect(p.get('date_to')).toBe('2026-11-30')
  expect(p.getAll('type')).toEqual(['expense'])
})

test('charts offer a table alternative and recent transactions are listed', async () => {
  const user = userEvent.setup()
  renderApp('/')
  expect(await screen.findByRole('img', { name: /Income and expenses for 2 months/ })).toBeInTheDocument()
  await user.click(screen.getAllByRole('button', { name: 'Show table' })[0]!)
  expect(await screen.findByRole('cell', { name: 'Nov 2026' })).toBeInTheDocument()
  const recent = await screen.findByRole('list', { name: 'Recent transactions' })
  expect(within(recent).getByText('Dinner')).toBeInTheDocument()
})

test('loading failure shows an inline error with retry', async () => {
  let calls = 0
  server.use(http.get(`${API}/dashboard/overview`, () => {
    calls += 1
    return calls === 1
      ? HttpResponse.json({ error: { code: 'internal_error', message: 'An unexpected error occurred', details: [] } }, { status: 500 })
      : HttpResponse.json({ data: overview(), meta: {} })
  }))
  const user = userEvent.setup()
  renderApp('/')
  const region = await screen.findByRole('region', { name: 'Key figures' })
  await user.click(await within(region).findByRole('button', { name: 'Retry' }))
  expect(await within(region).findByText('Total income')).toBeInTheDocument()
})

test('custom period waits for both dates and passes them to the API', async () => {
  let search = ''
  server.use(http.get(`${API}/dashboard/overview`, ({ request }) => {
    search = new URL(request.url).search
    return HttpResponse.json({ data: overview(), meta: {} })
  }))
  renderApp('/?period=custom&start=2026-07-15&end=2026-09-15')
  await waitFor(() => expect(search).toContain('period=custom'))
  expect(search).toContain('start=2026-07-15')
  expect(search).toContain('end=2026-09-15')
})

test('planning and balance sheet tiles show values and links', async () => {
  renderApp('/')
  const planning = await screen.findByRole('region', { name: 'Planning and balance sheet' })
  expect(within(planning).getByText('Net Worth')).toBeInTheDocument()
  expect(within(planning).getByText('₹25,00,000.00')).toBeInTheDocument()
  expect(within(planning).getByText('Total Assets')).toBeInTheDocument()
  expect(within(planning).getByText('₹35,00,000.00')).toBeInTheDocument()
  expect(within(planning).getByText('Total Liabilities')).toBeInTheDocument()
  expect(within(planning).getByText('₹10,00,000.00')).toBeInTheDocument()
  expect(within(planning).getByText('Outstanding Loans')).toBeInTheDocument()
  expect(within(planning).getByText('₹9,21,151.21')).toBeInTheDocument()
  expect(within(planning).getByText('Monthly EMI')).toBeInTheDocument()
  expect(within(planning).getByText('₹88,848.79')).toBeInTheDocument()
})

test('shows "Set a target" when savings target is not configured', async () => {
  server.use(
    http.get(`${API}/dashboard/overview`, () =>
      HttpResponse.json({
        data: overview({
          savings_target: {
            configured: false,
            target_amount: null,
            actual_savings: null,
            achievement_pct: null,
            shortfall: null,
          },
        }),
        meta: {},
      }),
    ),
  )
  renderApp('/')
  expect(await screen.findByRole('link', { name: 'Set a target' })).toBeInTheDocument()
})

test('budget alerts widget displays threshold crossed categories', async () => {
  renderApp('/')
  expect(await screen.findByText('Budget Status & Spending Alerts')).toBeInTheDocument()
  expect(screen.getByText('100%')).toBeInTheDocument()
  expect(screen.getByText('112.50%')).toBeInTheDocument()
})
