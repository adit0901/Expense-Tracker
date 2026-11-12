import { defineConfig, devices } from '@playwright/test'

/**
 * E2E against locally started servers (local PostgreSQL from scripts/dev-db.sh, Mailpit,
 * uvicorn and Vite). With Docker available, point BASE_URL at `docker compose up` instead
 * and set E2E_EXTERNAL=1 to skip starting servers.
 */
const external = !!process.env.E2E_EXTERNAL
// Dedicated ports so the run never attaches to some other local dev server.
const API_PORT = 8765
const WEB_PORT = 5199
const backendEnv = [
  'APP_ENV=development',
  'DATABASE_URL=postgresql+psycopg://fintrack_app:fintrack_app@localhost:54329/fintrack',
  'MIGRATION_DATABASE_URL=postgresql+psycopg://fintrack:fintrack@localhost:54329/fintrack',
  'SMTP_HOST=localhost',
  'SMTP_PORT=1025',
  `FRONTEND_BASE_URL=http://localhost:${WEB_PORT}`,
  'UPLOAD_DIR=../.local/uploads',
].join(' ')

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: [['list']],
  use: {
    baseURL: process.env.BASE_URL ?? `http://localhost:${WEB_PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: external ? undefined : [
    {
      command: 'mailpit --smtp 127.0.0.1:1025 --listen 127.0.0.1:8025',
      url: 'http://localhost:8025/api/v1/info',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `sh -c "cd ../backend && env ${backendEnv} uv run alembic upgrade head && env ${backendEnv} uv run uvicorn app.main:app --port ${API_PORT} --no-access-log 2>&1 | tee ../.local/e2e-backend.log"`,
      url: `http://localhost:${API_PORT}/health/ready`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: `npm run dev -- --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { VITE_API_PROXY: `http://localhost:${API_PORT}` },
      reuseExistingServer: !process.env.CI,
    },
  ],
})
