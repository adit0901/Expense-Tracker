import { http, HttpResponse } from 'msw'

import { API, server } from '@/test/server'

import { ApiError, api, setAuthFailureHandler, tokenStore } from './client'

test('refreshes once on 401 and retries with the new token', async () => {
  tokenStore.set('expired')
  let refreshCalls = 0
  server.use(
    http.post(`${API}/auth/refresh`, () => {
      refreshCalls += 1
      return HttpResponse.json({ data: { access_token: 'fresh', user: {} }, meta: {} })
    }),
    http.get(`${API}/accounts/summary`, ({ request }) =>
      request.headers.get('Authorization') === 'Bearer fresh'
        ? HttpResponse.json({ data: { liquid_funds: '1.00' }, meta: {} })
        : HttpResponse.json({ error: { code: 'not_authenticated', message: 'expired', details: [] } }, { status: 401 })),
  )
  // Two concurrent calls share one refresh (single flight).
  const [a, b] = await Promise.all([api.get('/accounts/summary'), api.get('/accounts/summary')])
  expect(a).toEqual({ liquid_funds: '1.00' })
  expect(b).toEqual({ liquid_funds: '1.00' })
  expect(refreshCalls).toBe(1)
  expect(tokenStore.get()).toBe('fresh')
})

test('refresh failure calls the auth-failure handler (redirect to login)', async () => {
  tokenStore.set('expired')
  const onFail = vi.fn()
  setAuthFailureHandler(onFail)
  server.use(
    http.post(`${API}/auth/refresh`, () => HttpResponse.json({ error: { code: 'invalid_refresh_token', message: 'no' } }, { status: 401 })),
    http.get(`${API}/accounts/summary`, () => HttpResponse.json({ error: { code: 'not_authenticated', message: 'expired', details: [] } }, { status: 401 })),
  )
  await expect(api.get('/accounts/summary')).rejects.toBeInstanceOf(ApiError)
  expect(onFail).toHaveBeenCalledTimes(1)
  expect(tokenStore.get()).toBeNull()
  setAuthFailureHandler(() => {})
})

test('maps the error envelope including field details', async () => {
  server.use(http.post(`${API}/transactions`, () => HttpResponse.json({
    error: { code: 'validation_error', message: 'Request validation failed', request_id: 'r1',
      details: [{ field: 'amount', message: 'Input should be greater than 0' }] },
  }, { status: 422 })))
  const err = (await api.post('/transactions', {}).catch((e: unknown) => e)) as ApiError
  expect(err.status).toBe(422)
  expect(err.code).toBe('validation_error')
  expect(err.requestId).toBe('r1')
  expect(err.fieldErrors()).toEqual({ amount: 'Input should be greater than 0' })
})

test('the access token is never written to web storage', async () => {
  tokenStore.set('secret-token')
  await api.get('/accounts/summary')
  expect(JSON.stringify({ ...localStorage })).not.toContain('secret-token')
  expect(JSON.stringify({ ...sessionStorage })).not.toContain('secret-token')
})
