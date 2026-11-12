import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { expect, test } from 'vitest'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

const mockNetWorth = {
  as_of: '2026-11-12',
  total_assets: '670000.00',
  total_liabilities: '4825000.00',
  net_worth: '-4155000.00',
  liquid_assets: '300000.00',
  asset_breakdown: [
    { category: 'Bank & Cash', amount: '300000.00', share_pct: '44.78' },
    { category: 'Fixed Deposits', amount: '205000.00', share_pct: '30.60' },
    { category: 'Gold', amount: '165000.00', share_pct: '24.62' },
  ],
  liability_breakdown: [
    { category: 'Credit Card', amount: '25000.00', share_pct: '0.52' },
    { category: 'Home Loan', amount: '4800000.00', share_pct: '99.48' },
  ],
  mom_growth: {
    amount_change: '50000.00',
    percentage_change: '5.00',
  },
  yoy_growth: null,
  is_stale: true,
}

const mockSnapshots = [
  {
    id: 's-1',
    as_of: '2026-10-31',
    total_assets: '620000.00',
    total_liabilities: '4825000.00',
    net_worth: '-4205000.00',
    breakdown: {},
    computed_at: '2026-10-31T23:59:59Z',
    is_stale: false,
  },
]

const mockAssets = [
  {
    id: 'a-1',
    name: 'HDFC 2-Year FD',
    type: 'fixed_deposit' as const,
    is_liquid: true,
    current_value: '205000.00',
    latest_valuation_date: '2026-11-01',
    details: {},
    closed_at: null,
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
  },
]

const mockLiabilities = [
  {
    id: 'l-1',
    name: 'Loan from Uncle',
    current_balance: '80000.00',
    latest_balance_date: '2026-11-01',
    notes: 'Repay by end of year',
    closed_at: null,
    created_at: '2026-11-01T00:00:00Z',
    updated_at: '2026-11-01T00:00:00Z',
  },
]

function setupNetWorthHandlers() {
  server.use(
    http.get(`${API}/net-worth`, () =>
      HttpResponse.json({ data: mockNetWorth, meta: {} }),
    ),
    http.get(`${API}/net-worth/snapshots`, () =>
      HttpResponse.json({ data: mockSnapshots, meta: {} }),
    ),
    http.get(`${API}/assets`, () =>
      HttpResponse.json({ data: mockAssets, meta: {} }),
    ),
    http.get(`${API}/liabilities`, () =>
      HttpResponse.json({ data: mockLiabilities, meta: {} }),
    ),
    http.get(`${API}/assets/:id/valuations`, () =>
      HttpResponse.json({
        data: [
          {
            id: 'v-1',
            asset_id: 'a-1',
            value: '205000.00',
            as_of: '2026-11-01',
            created_at: '2026-11-01T00:00:00Z',
          },
        ],
        meta: {},
      }),
    ),
  )
}

test('renders net worth totals, MoM growth and missing YoY growth dash', async () => {
  setupNetWorthHandlers()
  renderApp('/net-worth')

  expect(await screen.findByRole('heading', { name: 'Net Worth' })).toBeInTheDocument()
  expect(await screen.findByText('-₹41,55,000.00')).toBeInTheDocument()
  expect(screen.getByText('₹6,70,000.00')).toBeInTheDocument()
  expect(screen.getByText('₹48,25,000.00')).toBeInTheDocument()

  // MoM growth
  expect(screen.getByText(/5\.00%/i)).toBeInTheDocument()
  // YoY growth missing: renders "—"
  expect(screen.getAllByText('—').length).toBeGreaterThan(0)

  // Stale badge
  expect(screen.getByText('Outdated')).toBeInTheDocument()
})

test('allows recomputing net worth when stale', async () => {
  let recomputedDate: string | null = null
  setupNetWorthHandlers()
  server.use(
    http.post(`${API}/net-worth/snapshots/:as_of/recompute`, ({ params }) => {
      recomputedDate = String(params.as_of)
      return HttpResponse.json({
        data: {
          id: 's-recomputed',
          as_of: params.as_of,
          total_assets: '670000.00',
          total_liabilities: '4825000.00',
          net_worth: '-4155000.00',
          breakdown: {},
          computed_at: new Date().toISOString(),
          is_stale: false,
        },
        meta: {},
      })
    }),
  )

  const user = userEvent.setup()
  renderApp('/net-worth')

  const recomputeBtn = await screen.findByRole('button', { name: 'Recompute net worth' })
  await user.click(recomputeBtn)

  await waitFor(() => {
    expect(recomputedDate).toBe('2026-11-12')
  })
})

test('displays assets, liabilities and valuation history', async () => {
  setupNetWorthHandlers()
  const user = userEvent.setup()
  renderApp('/net-worth')

  expect(await screen.findByText('HDFC 2-Year FD')).toBeInTheDocument()
  expect(screen.getByText('Loan from Uncle')).toBeInTheDocument()

  const historyBtn = screen.getByRole('button', { name: 'Valuation history for HDFC 2-Year FD' })
  await user.click(historyBtn)

  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByText(/Valuation History: HDFC 2-Year FD/i)).toBeInTheDocument()
  expect(within(dialog).getByText('₹2,05,000.00')).toBeInTheDocument()
})
