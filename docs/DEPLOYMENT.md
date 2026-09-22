# SuryaSetu — production deployment

This document describes how to run SuryaSetu outside local development.
SQLite remains the default for development. PostgreSQL is recommended for production.

## Environments

| `ENVIRONMENT` | Behaviour |
|---|---|
| `development` (default) | Dev OTP `1234` is accepted and returned in API responses. `/docs` is enabled. Cookies are not marked Secure. Seed script is allowed. |
| `test` | Same as development for OTP, but used by pytest. Rate limiting is disabled by the test harness. |
| `production` | Dev OTP is **disabled**. OTP codes are never returned in API responses. `/docs`, `/redoc` and `/openapi.json` are disabled. Auth cookies are `Secure` + `HttpOnly` + `SameSite=Lax`. Seed refuses to run unless `FORCE_SEED=1`. Stack traces are never returned. |

Never ship demo credentials to production. The accounts created by `scripts/seed.py` (`primary` / `ChangeMe123!`, mobile `9999999999` / OTP `1234`) exist only for local demonstration.

## Minimum production environment

```
ENVIRONMENT=production
SECRET_KEY=<long random value>
DATABASE_URL=postgresql+psycopg2://suryasetu:****@db:5432/suryasetu
UPLOAD_DIR=/var/lib/suryasetu/uploads
RATE_LIMIT_ENABLED=true
SMS_API_URL=https://your-sms-gateway.example/send
SMS_API_TOKEN=****
```

Generate a secret:

```
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Process

Run a single uvicorn worker with SQLite. For PostgreSQL you may run several workers
behind a reverse proxy:

```
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 1
```

Put nginx / Caddy in front for TLS. Forward `/` to the app. Do not expose the
database port.

## Reverse-proxy rate limiting

The in-app limiter is per-process. For multiple workers, also rate-limit at the proxy:

- `/api/auth/otp/send`, `/api/auth/otp/verify`, `/api/auth/admin/login`
- `/api/public/contact`
- `/api/admin/export/*`

## Scheduled warranty scan

The app runs a scan on startup and staff can click **Scan Expiring**. In production
also schedule:

```
0 */6 * * *  cd /opt/suryasetu && ENVIRONMENT=production python -m app.jobs.warranty_scan
```

The job is idempotent: a panel is notified at most once while it remains `EXPIRING_SOON`.

## Notification providers

| Channel | Env vars | Development fallback |
|---|---|---|
| In-app | none | always on |
| Email | `SMTP_HOST`, `SMTP_USERNAME`, `SMTP_PASSWORD` | console mock |
| SMS | `SMS_API_URL`, `SMS_API_TOKEN` | console mock |
| WhatsApp | `WHATSAPP_API_URL`, `WHATSAPP_API_TOKEN` | console mock |

Do not put provider secrets in source control.

## File storage

- Development: `uploads/` in the project directory.
- Production: set `UPLOAD_DIR` to a persistent volume.
- Client documents are **not** publicly served. Download goes through
  `/api/client/documents/{id}/file` and `/api/admin/documents/{id}/file`
  after authorization.
- Branding images are public at `/uploads/branding/`.
- Allowed document types: PDF, JPEG, PNG, WebP. Executables are rejected.
- Max size: `MAX_UPLOAD_BYTES` (default 10 MB).

## Health checks

- Liveness: `GET /health` → `{ "status": "ok" }`
- Readiness: `GET /health/ready` → `{ "status": "ready" }` (checks the database)
- Compatibility: `GET /api/health`

Do not use `/docs` as a health check in production (it is disabled).

## PostgreSQL

See [POSTGRES.md](POSTGRES.md). Panel allocation uses `SELECT ... FOR UPDATE` on
PostgreSQL and an in-process lock on SQLite.

## Logging

Structured JSON logs to stdout. Fields include timestamp, level, method, path,
status, duration, user id and role when a session exists. Passwords, OTPs,
tokens and document contents are never logged.
