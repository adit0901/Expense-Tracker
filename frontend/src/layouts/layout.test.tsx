import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'

import { COMING_SOON_ROUTES, NAVIGATION } from '@/app/navigation'
import { requests } from '@/test/server'
import { renderApp } from '@/test/utils'

const ALLOWED_BACKGROUND_CALLS = ['/auth/refresh', '/users/me/preferences']

test('navigation lists all sections and highlights the current one', async () => {
  renderApp('/transactions')
  const nav = (await screen.findAllByRole('navigation', { name: 'Main navigation' }))[0]!
  for (const item of NAVIGATION) {
    expect(within(nav).getByRole('link', { name: new RegExp(`^${item.label.replace(/[&]/g, '\\$&')}`) })).toBeInTheDocument()
  }
  for (const sub of ['Indian Stocks', 'US Stocks', 'Portfolio Overview', 'Home Loans', 'Car Loans', 'Other Loans']) {
    expect(within(nav).getByRole('link', { name: sub })).toBeInTheDocument()
  }
  expect(within(nav).getByRole('link', { name: /^Transactions/ })).toHaveAttribute('aria-current', 'page')
})

test.each(COMING_SOON_ROUTES.map((r) => [r.label, r.to]))(
  '%s shows coming soon and makes no feature API calls',
  async (label, to) => {
    renderApp(to)
    expect(await screen.findByText('Coming in a later release')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1, name: label })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    const featureCalls = requests.filter((r) => !ALLOWED_BACKGROUND_CALLS.includes(r.path))
    expect(featureCalls).toEqual([])
  },
)

test('mobile menu button opens the navigation drawer', async () => {
  const user = userEvent.setup()
  renderApp('/budgets')
  await user.click(await screen.findByRole('button', { name: 'Open navigation menu' }))
  const dialog = await screen.findByRole('dialog')
  expect(within(dialog).getByRole('link', { name: /^Overview/ })).toBeInTheDocument()
})

test('signing out goes to login without a back-link', async () => {
  const user = userEvent.setup()
  const { router } = renderApp('/transactions')
  await user.click(await screen.findByRole('button', { name: 'Sign out' }))
  await screen.findByRole('heading', { name: 'Sign in' })
  expect(router.state.location.pathname).toBe('/login')
  expect(router.state.location.search).toBe('')
})
