import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { API, server } from '@/test/server'
import { renderApp } from '@/test/utils'

function loggedOut() {
  server.use(http.post(`${API}/auth/refresh`, () =>
    HttpResponse.json({ error: { code: 'invalid_refresh_token', message: 'none', details: [] } }, { status: 401 })))
}

test('login shows client-side validation inline', async () => {
  loggedOut()
  const user = userEvent.setup()
  renderApp('/login')
  await user.click(await screen.findByRole('button', { name: /sign in/i }))
  expect(await screen.findByText('Enter a valid email address')).toBeInTheDocument()
  expect(screen.getByText('Enter your password')).toBeInTheDocument()
  expect(screen.getByLabelText('Email')).toHaveAttribute('aria-invalid', 'true')
})

test('login server error is shown and input is preserved', async () => {
  loggedOut()
  server.use(http.post(`${API}/auth/login`, () => HttpResponse.json({
    error: { code: 'invalid_credentials', message: 'Invalid email or password', details: [] },
  }, { status: 401 })))
  const user = userEvent.setup()
  renderApp('/login')
  await user.type(await screen.findByLabelText('Email'), 'asha@example.com')
  await user.type(screen.getByLabelText('Password'), 'wrong-password-1')
  await user.click(screen.getByRole('button', { name: /sign in/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent('Invalid email or password')
  expect(screen.getByLabelText('Email')).toHaveValue('asha@example.com')
  expect(screen.getByLabelText('Password')).toHaveValue('wrong-password-1')
})

test('register maps server field errors next to the field and keeps values', async () => {
  loggedOut()
  server.use(http.post(`${API}/auth/register`, () => HttpResponse.json({
    error: { code: 'weak_password', message: 'Password is too common; choose a less predictable password',
      details: [{ field: 'password', message: 'too_common' }] },
  }, { status: 422 })))
  const user = userEvent.setup()
  renderApp('/register')
  await user.type(await screen.findByLabelText('Full name'), 'Asha Rao')
  await user.type(screen.getByLabelText('Email'), 'asha@example.com')
  await user.type(screen.getByLabelText('Password'), 'password123')
  await user.type(screen.getByLabelText('Confirm password'), 'password123')
  await user.click(screen.getByRole('button', { name: /create account/i }))
  const pw = screen.getByLabelText('Password')
  await waitFor(() => expect(pw).toHaveAttribute('aria-invalid', 'true'))
  expect(screen.getByText(/too common/i)).toBeInTheDocument()
  expect(screen.getByLabelText('Full name')).toHaveValue('Asha Rao')
  expect(pw).toHaveValue('password123')
})

test('register validates matching passwords and minimum length', async () => {
  loggedOut()
  const user = userEvent.setup()
  renderApp('/register')
  await user.type(await screen.findByLabelText('Password'), 'short')
  await user.type(screen.getByLabelText('Confirm password'), 'different')
  await user.click(screen.getByRole('button', { name: /create account/i }))
  expect(await screen.findByText('Password must be at least 10 characters')).toBeInTheDocument()
  expect(screen.getByText('Passwords do not match')).toBeInTheDocument()
})

test('forgot password shows the same generic confirmation', async () => {
  loggedOut()
  server.use(http.post(`${API}/auth/password-reset/request`, () => HttpResponse.json({
    data: { message: 'If an account exists for that email, a reset link has been sent.' }, meta: {} }, { status: 202 })))
  const user = userEvent.setup()
  renderApp('/forgot-password')
  await user.type(await screen.findByLabelText('Email'), 'nobody@example.com')
  await user.click(screen.getByRole('button', { name: /send reset link/i }))
  expect(await screen.findByRole('status')).toHaveTextContent('If an account exists')
})

test('reset password reports an expired link and keeps input', async () => {
  loggedOut()
  server.use(http.post(`${API}/auth/password-reset/confirm`, () => HttpResponse.json({
    error: { code: 'reset_token_invalid', message: 'Reset link is invalid or has expired', details: [] } }, { status: 400 })))
  const user = userEvent.setup()
  renderApp('/reset-password?token=abcdefghijkl')
  await user.type(await screen.findByLabelText('New password'), 'Brand-New-Secret-77')
  await user.type(screen.getByLabelText('Confirm new password'), 'Brand-New-Secret-77')
  await user.click(screen.getByRole('button', { name: /update password/i }))
  expect(await screen.findByRole('alert')).toHaveTextContent('expired')
  expect(screen.getByLabelText('New password')).toHaveValue('Brand-New-Secret-77')
})

test('change password shows wrong-current-password error', async () => {
  server.use(http.post(`${API}/auth/password/change`, () => HttpResponse.json({
    error: { code: 'invalid_current_password', message: 'Current password is incorrect',
      details: [{ field: 'current_password', message: 'incorrect' }] } }, { status: 400 })))
  const user = userEvent.setup()
  renderApp('/settings/security')
  await user.type(await screen.findByLabelText('Current password'), 'Wrong-pass-12')
  await user.type(screen.getByLabelText('New password'), 'New-Secret-123')
  await user.type(screen.getByLabelText('Confirm new password'), 'New-Secret-123')
  await user.click(screen.getByRole('button', { name: /change password/i }))
  await waitFor(() => expect(screen.getByLabelText('Current password')).toHaveAttribute('aria-invalid', 'true'))
  expect(screen.getAllByText('Current password is incorrect').length).toBeGreaterThan(0)
})

test('deep link while logged out goes to login, then back after sign-in', async () => {
  loggedOut()
  const user = userEvent.setup()
  const { router } = renderApp('/transactions?type=expense')
  await screen.findByRole('heading', { name: 'Sign in' })
  expect(router.state.location.pathname).toBe('/login')
  expect(router.state.location.search).toContain(encodeURIComponent('/transactions?type=expense'))
  await user.type(screen.getByLabelText('Email'), 'asha@example.com')
  await user.type(screen.getByLabelText('Password'), 'Correct-Horse-1')
  await user.click(screen.getByRole('button', { name: /sign in/i }))
  await screen.findByRole('heading', { name: 'Transactions' })
  expect(router.state.location.pathname).toBe('/transactions')
  expect(router.state.location.search).toBe('?type=expense')
})
