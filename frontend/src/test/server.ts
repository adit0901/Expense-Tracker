import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'

import type { TransactionOut } from '@/services/api/types'

import { ACCOUNT, CARD, CATEGORIES, PREFS, USER, overview, txn } from './fixtures'

export const API = 'http://localhost:3000/api/v1'

/** Requests seen by the mock server (path + search), for asserting what the UI called. */
export const requests: { method: string; path: string; search: string }[] = []

export const db = { transactions: [txn()] as TransactionOut[] }
export function resetDb() {
  db.transactions = [txn()]
  requests.length = 0
}

const page = <T,>(data: T[], extra: Record<string, unknown> = {}) =>
  HttpResponse.json({ data, meta: { page: 1, page_size: 25, total_items: data.length, total_pages: 1, ...extra } })

const month = (m: string, label: string, income: string, expenses: string, savings: string, rate: string | null) =>
  ({ month: m, label, income, expenses, savings, savings_rate: rate })

export const handlers = [
  http.post(`${API}/auth/refresh`, () => HttpResponse.json({ data: { access_token: 'tok-refreshed', token_type: 'bearer', expires_in: 900, user: USER }, meta: {} })),
  http.post(`${API}/auth/login`, () => HttpResponse.json({ data: { access_token: 'tok-login', token_type: 'bearer', expires_in: 900, user: USER }, meta: {} })),
  http.post(`${API}/auth/logout`, () => new HttpResponse(null, { status: 204 })),
  http.get(`${API}/users/me/preferences`, () => HttpResponse.json({ data: PREFS, meta: {} })),
  http.get(`${API}/accounts`, () => page([ACCOUNT, CARD])),
  http.get(`${API}/accounts/summary`, () => HttpResponse.json({ data: { liquid_funds: '120000.00', bank_balance: '118000.00', cash_balance: '2000.00', wallet_balance: '0.00', credit_card_outstanding: '5000.00', currency: 'INR' }, meta: {} })),
  http.get(`${API}/categories`, () => page(CATEGORIES)),
  http.get(`${API}/income-sources`, () => page([])),
  http.get(`${API}/transactions`, () => page(db.transactions, { totals: { count: db.transactions.length, total_amount: '450.00', income: '0.00', expense: '450.00', refund: '0.00', transfer: '0.00', net_expense: '450.00' } })),
  http.get(`${API}/dashboard/overview`, () => HttpResponse.json({ data: overview(), meta: {} })),
  http.get(`${API}/dashboard/trends`, () => HttpResponse.json({ data: { period: overview().period, months: [
    month('2026-10', 'Oct 2026', '100000.00', '60000.00', '40000.00', '40.00'),
    month('2026-11', 'Nov 2026', '120000.00', '90000.00', '30000.00', '25.00'),
  ] }, meta: {} })),
  http.get(`${API}/dashboard/category-breakdown`, () => HttpResponse.json({ data: { period: overview().period, total_expenses: '90000.00', categories: [
    { category_id: 'cat-food', name: 'Food', color: '#000', total: '60000.00', share: '66.67', is_other: false },
    { category_id: null, name: 'Other categories', color: null, total: '30000.00', share: '33.33', is_other: true },
  ] }, meta: {} })),
]

export const server = setupServer(...handlers)

// Record every request (including ones answered by per-test overrides).
server.events.on('request:start', ({ request }) => {
  const url = new URL(request.url)
  requests.push({ method: request.method, path: url.pathname.replace('/api/v1', ''), search: url.search })
})
