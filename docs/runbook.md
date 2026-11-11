# FinTrack runbook

Operational guide for running FinTrack P0: a single API instance, PostgreSQL, SMTP and a
local receipts volume.

## Components

| Component | Process | State |
|---|---|---|
| API | `uvicorn app.main:app --no-access-log` (container: `infrastructure/backend.Dockerfile`) | Stateless, except for in-memory rate-limit counters |
| Web | Static build served by nginx (`infrastructure/frontend.Dockerfile`), which proxies `/api` and `/health` | None |
| Database | PostgreSQL 16 or later | All user data and the audit log |
| Receipts | `UPLOAD_DIR` volume (`/data/uploads` in containers) | Uploaded files, named by random keys |
| Email | Any SMTP server (Mailpit in development) | None |

## Health checks

- `GET /health/live` returns 200 while the process is up. Use it as the liveness probe.
- `GET /health/ready` returns 200 when the database is reachable and migrations are at head.
  Otherwise it returns 503 with `error.details[0].dependency` set to `database` or
  `migrations`. Use it as the readiness probe and for deploy gates.

## Configuration and secrets

- Configuration comes only from environment variables (see `.env.example`).
- With `APP_ENV=production`, start-up **fails** in these cases:
  - `JWT_SECRET` is missing, is the development default, or is shorter than 32 characters;
  - `DATABASE_URL` is not set explicitly.
- Generate a JWT secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
- **Rotating `JWT_SECRET`** invalidates every access token. Refresh tokens are opaque and
  stored hashed, so they keep working, and clients recover with one silent refresh. Rotate
  during low traffic.
- Use two database roles:
  - the owner (`MIGRATION_DATABASE_URL`) runs migrations;
  - the application role (`DATABASE_URL`) serves traffic and has no UPDATE, DELETE or
    TRUNCATE right on `audit_log`.

## Deploying

1. Build the images.
2. Run `alembic upgrade head` as the owner role. The backend container does this on start;
   for multiple replicas, run it once as a separate job.
3. Roll out the API and wait for `/health/ready` to return 200.
4. Roll out the web image.

Migrations are forward-only in normal operation, and every revision has a tested downgrade.
CI runs upgrade, then downgrade to base, then upgrade again.

**Rollback:** redeploy the previous image, then run `alembic downgrade -1` (once per
revision being reverted) as the owner role. Check the downgrade first: a downgrade that drops
tables loses their data.

## Backups and restore

- Back up the database daily with `pg_dump --format=custom --no-owner "$OWNER_URL" > fintrack-$(date +%F).dump`.
- Back up the receipts volume at the same time (for example with `tar` or a volume snapshot).
  Database rows refer to files by `attachments.storage_key`.
- To restore:
  1. Run `pg_restore --clean --if-exists --no-owner -d "$OWNER_URL" fintrack-YYYY-MM-DD.dump`.
  2. Restore the uploads volume.
  3. Re-apply the application-role grants by re-running `alembic upgrade head`. Migration
     `0001` sets default privileges and `0002` revokes audit-log writes.
- Test a restore every quarter.

## Logs

- The API writes one JSON line per request with these fields:
  - `request_id` (also in the `X-Request-ID` response header and in every error body);
  - `method`;
  - `route`, the route template, never the raw URL;
  - `status`;
  - `duration_ms`;
  - `user_id`.
- A redaction processor masks any key containing password, token, secret, authorization,
  cookie, amount, balance, description, notes, payee, account_number, last4, reset_link,
  gross or deduction.
- **Keep uvicorn's own access log disabled** (`--no-access-log`). It prints full URLs with
  query strings, which can contain search text and amount filters.
- To trace a user report, ask for the `request_id` shown in the error, then search the logs
  for it.

## Audit trail

- Every create, update and delete of accounts, categories, transactions, attachments, income
  sources and imports adds a row to `audit_log`. Each row records the actor, action, entity
  type and id, the changed field **names** (never values), the request id and the time.
- The application role cannot modify or delete audit rows.
- When a user deletes their account, their audit rows are kept but anonymized
  (`actor_user_id` set to NULL) by the `anonymize_audit_actor` SECURITY DEFINER function.

## Rate limiting

- **Failed logins:** 5 per 15 minutes per client IP and per email. A further attempt returns
  429 with `Retry-After`, even with the right password. A successful login resets the email
  counter.
- **General API:** `API_RATE_LIMIT` per user (or per IP when unauthenticated).
- Counters are in memory and reset when the process restarts. They are not shared across
  replicas, so run a single API instance until Redis-backed limits arrive in P1.
- Behind a proxy, make sure the real client IP reaches uvicorn. Use `--proxy-headers` and
  `--forwarded-allow-ips` with your proxy's address. Otherwise every user shares one IP
  counter.

## Common incidents

| Symptom | Likely cause | Action |
|---|---|---|
| `/health/ready` returns 503 `database` | Database down, or wrong `DATABASE_URL` / network | Check database status and credentials. The API recovers by itself (connections use pre-ping). |
| `/health/ready` returns 503 `migrations` | New image deployed without migrating | Run `alembic upgrade head` as the owner role |
| Start-up fails with `Invalid production configuration` | Default or missing secret | Set `JWT_SECRET` and `DATABASE_URL` |
| Users don't receive reset emails | SMTP unreachable. The API logs `email_failed` and still returns 202, by design. | Check the SMTP host and port, and the provider's logs |
| Uploads fail with 500 | `UPLOAD_DIR` not writable or full | Check the volume's permissions and free space |
| Many 429s on login from one office | Shared NAT IP | Expected protection. Wait for `Retry-After`, or raise limits in code if justified. |
| Many 401s after a deploy | `JWT_SECRET` changed | Expected. Clients refresh silently. |

## Data subject requests

- **Delete:** the user deletes their own account in **Settings → Delete account**. This
  cascades to all their rows and removes their receipt files. Audit rows are anonymized.
- **Export:** the user can export transactions as CSV from Transactions and reports from
  **Reports & Analytics**.
