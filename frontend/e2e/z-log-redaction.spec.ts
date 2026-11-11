/**
 * Runs last (alphabetical, single worker): scans the backend log produced during the E2E run
 * for sensitive values that must never be logged.
 */
import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { expect, test } from '@playwright/test'

import { PASSWORD } from './helpers'

const LOG = resolve(process.cwd(), '../.local/e2e-backend.log')

test('backend logs contain no amounts, descriptions, passwords or tokens', () => {
  test.skip(!existsSync(LOG), 'backend log not captured (servers started externally)')
  const log = readFileSync(LOG, 'utf8')
  expect(log.length).toBeGreaterThan(0)
  const forbidden = [
    PASSWORD, 'Brand-New-Secret-77',                       // passwords
    '123000', '20450', '450.00', '150000', '25000.00',     // amounts
    'Swiggy', 'Dinner', 'Uber ride', 'November salary',    // descriptions
    'fintrack_refresh=', 'Bearer ', 'token=', 'eyJ',       // tokens / JWTs / reset links
  ]
  const leaks = forbidden.filter((s) => log.includes(s))
  expect(leaks).toEqual([])
  // Request lines are structured JSON with a request id and route template.
  const lines = log.split('\n').filter((l) => l.startsWith('{') && l.includes('"event": "request"'))
  expect(lines.length).toBeGreaterThan(10)
  const sample = JSON.parse(lines[0]!) as Record<string, unknown>
  expect(Object.keys(sample)).toEqual(expect.arrayContaining(['request_id', 'method', 'route', 'status', 'duration_ms']))
})
