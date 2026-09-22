# SuryaSetu — Solar Energy Management Platform

## Client, staff and public UI (Phase 3)

Every important user-facing API is wired to a screen:

- **Client portal** — dashboard, profile/KYC, connection, project/installation, panels, warranty claims (submit + timeline), payments, documents, generation (today / week / month / lifetime), services, support tickets with replies, notifications, settings.
- **Staff console** — operations dashboard, clients, projects, allocation, warranty claims (controlled transitions), payments, services, tickets with conversation, documents, enquiries, reports + CSV, audit, notifications. Super Admin adds staff, reports, audit. Primary Admin adds website CMS, FAQs, announcements, branding upload, permission matrix, system settings.
- **Public website** — home, about, solar, how it works, services, public projects, FAQ, contact form. Content is database-backed.

Demo client: mobile `9999999999`, OTP `1234`. Staff: `primary` / `superadmin` / `admin` with password `ChangeMe123!`.

SQLite is for development. Panel allocation uses an in-process lock; for multi-process production use PostgreSQL row locks.


A real, working full-stack solar-capacity subscription platform: **FastAPI + SQLAlchemy +
SQLite backend**, server-rendered **Jinja2 + vanilla JS frontend**, styled with the PV-cell
dark theme from the original `suryaSetu.html` prototype (deep silicon-blue background, amber
for energy/money-due, green for settled, the six-stage installation "busbar").

Everything here actually talks to the backend. There is no client-side mock state standing
in for real data — SQLite is the single source of truth, panel allocation runs FIFO inside a
real database transaction, and RBAC is enforced server-side on every endpoint.

## What's implemented (and genuinely working, not stubbed)

- **Auth & RBAC** — OTP login/registration for clients, username/password login for
  Admin / Super Admin / Primary Admin. JWT session cookie. A role → permission map is
  enforced on every protected endpoint (see `app/permissions.py`), not just hidden in the UI.
- **Role hierarchy** — Primary Admin > Super Admin > Admin > Client, with server-side checks
  (an Admin cannot create/edit a Super Admin; only Primary Admin can).
- **Client onboarding** — mirrors the original prototype: mobile OTP → PAN OTP-style
  verification → Aadhaar → electricity bill upload/OCR-simulation → proposed plant sizing →
  project & panel allocation → six-stage installation tracker → payments → generation.
- **New vs. existing client** — a returning client goes straight to their dashboard; a new
  client sees the onboarding flow, driven by `ClientProfile.onboarding_stage`.
- **Projects & panel inventory** — multiple solar sites, each with a real panel inventory
  (`Panel` rows with a monotonic `added_sequence`).
- **FIFO panel allocation** — `app/services/allocation_service.py`. Allocation always takes
  the lowest `added_sequence` AVAILABLE panels first, inside a serialized critical section
  (a process-wide lock plus an atomic DB commit) so two concurrent allocation requests can't
  double-allocate the same panel. Verified by `tests/test_core.py::test_fifo_allocation_order`.
- **Project capacity alerts** — configurable warning (80%) / critical (90%) / full (100%)
  thresholds. Crossing a threshold updates `Project.status` and fires notifications to the
  correct roles. Verified live: allocating to 90% flips the project to `NEAR_CAPACITY` and
  notifies Admin+Super Admin+Primary Admin; reaching 100% flips it to `FULL` and blocks all
  further allocation with a clear error.
- **Notification routing** — `app/services/notification_service.py` implements the routing
  table from the spec (new client / first payment / client question / service request →
  Admin + Super Admin; capacity warnings → + Primary Admin). An `EmailNotifier` /
  `WhatsAppNotifier` / `SMSNotifier` abstraction exists in `app/services/notifiers.py` — each
  falls back to a console "mock" provider when no credentials are configured, so the whole
  app works with zero external accounts, and can be pointed at real SMTP/WhatsApp/SMS
  providers later purely via `.env`.
- **Payments** — a real ledger; paying a stage automatically marks it `COMPLETED` and unlocks
  the next stage; the client's first successful payment is auto-detected and notified.
- **Documents** — uploaded to `uploads/clients/<client_id>/<type>/`, tracked in SQLite with
  status (`UPLOADED` → `VERIFIED`/`REJECTED` by an admin).
- **Services & support tickets** — clients can request extra services and open tickets; staff
  can quote/approve/track them.
- **Audit log** — every administrative mutation (panel allocation/deallocation, stage
  updates, payments, staff creation/removal, project changes, document verification) is
  recorded with actor, before/after values and timestamp.
- **Generation** — deterministic-but-randomised daily generation history, seeded per client,
  matching the seasonal Bengaluru irradiance curve from the prototype.

## What's intentionally scoped down

This was built to make the *hard* parts (RBAC, FIFO allocation, capacity alerting, payment →
stage progression, notification routing, audit logging) real and tested rather than padding
out every peripheral module with placeholder code. Left as clear extension points:

- **Email/WhatsApp/SMS** — console-mock only; the abstraction is in place, real provider
  calls are a few lines inside `app/services/notifiers.py` once you have credentials.
- **Website CMS** (`WebsiteContent` model exists; no admin UI to edit it yet).
- **Reports** are basic (revenue total, project utilization) rather than full charts.
- **Ticket threaded messages** (`TicketMessage` model exists; only ticket status is wired
  into the UI, not a full conversation thread).
- Production-grade row locking for allocation (SQLite has no `SELECT ... FOR UPDATE`; the
  in-process lock in `allocation_service.py` is documented and sufficient for a single-process
  dev/demo deployment, but should become a real row lock — e.g. Postgres
  `SELECT ... FOR UPDATE SKIP LOCKED` — for a multi-process production deployment).

## Installation

```bash
cd suryasetu
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env              # edit if you want real SMTP/WhatsApp/SMS later
```

## Initialize & seed the database

```bash
python scripts/seed.py
```

This drops and recreates `suryasetu.db`, then creates:

- 1 Primary Admin, 2 Super Admins, 5 Admins
- 3 solar projects (Chennai, Bengaluru, Hyderabad), 120 panels each
- 10 clients in various onboarding states, 6 of them with panels allocated, stages created,
  some payments recorded, and ~60 days of simulated generation history
- A starter service catalog, a couple of sample service requests and support tickets

## Run

```bash
uvicorn app.main:app --reload
```

Then open:

- **Public site** — http://127.0.0.1:8000/
- **Client sign-in** — http://127.0.0.1:8000/login (mobile OTP; dev OTP is always `1234`)
- **Staff sign-in** — http://127.0.0.1:8000/staff-login
- **API docs (Swagger)** — http://127.0.0.1:8000/docs
- **API docs (ReDoc)** — http://127.0.0.1:8000/redoc

### Development login credentials

```
Primary Admin  ->  username: primary       password: ChangeMe123!
Super Admin    ->  username: superadmin    password: ChangeMe123!
Admin          ->  username: admin         password: ChangeMe123!
```

**Demo Client (recommended for Client portal testing):**

```
Name   : Demo Solar Customer
Mobile : 9999999999
OTP    : 1234
Email  : demo.client@example.com
```

This account is fully seeded with KYC, documents, a Chennai project allocation (10×400W panels),
installation stages (through Installation IN_PROGRESS), payments, generation history, a service
request, a support ticket, and notifications. On the client login page you can also click
**Use Demo Solar Customer** for one-click access (development only).

Other client accounts sign in with any 10-digit mobile number; the OTP screen shows the dev code
(always `1234`) directly since no real SMS gateway is configured.

**Change these before any non-local use.** They are seeded only for development.
When `ENVIRONMENT=production`, the fixed OTP is disabled, OTP codes are never
returned by the API, `/docs` is turned off, and `scripts/seed.py` refuses to
run (it drops the database).


## Running the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

The suite covers authentication, RBAC, FIFO allocation, warranty claims and
transitions, CSV export (including formula-injection sanitization and audit),
the public website, contact enquiries, document IDOR and upload policy,
payments, ticket conversations, health checks and basic security contracts.

Tests force `ENVIRONMENT=test` and use a separate SQLite file
(`test_suryasetu.db`). They never touch the development `suryasetu.db`.

## Production, PostgreSQL, backup

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — environments, secrets, health checks, notifications, scheduled warranty scan, reverse proxy
- [docs/POSTGRES.md](docs/POSTGRES.md) — switching from SQLite to PostgreSQL
- [docs/BACKUP.md](docs/BACKUP.md) — database and upload backup / restore

Set `ENVIRONMENT=production` and a strong `SECRET_KEY` before exposing the app.
Demo accounts and the development OTP (`1234`) are **disabled in production**.

Health:

- `GET /health` — liveness
- `GET /health/ready` — database reachable
- `GET /api/health` — compatibility

Warranty scan (cron):

```bash
python -m app.jobs.warranty_scan
```


## Folder structure

```
suryasetu/
├── app/
│   ├── main.py                 FastAPI app, mounts static/uploads, registers routers
│   ├── config.py                Settings (env-driven)
│   ├── database.py              SQLAlchemy engine/session
│   ├── dependencies.py          get_current_user / require_roles / require_permission
│   ├── security.py              password hashing + JWT
│   ├── permissions.py           role -> permission map
│   ├── models.py                every SQLAlchemy model (users, clients, projects, panels,
│   │                             stages, payments, documents, services, tickets,
│   │                             notifications, audit log, settings, website content)
│   ├── schemas.py                Pydantic request/response models
│   ├── routers/
│   │   ├── pages.py              Jinja2 page routes (/, /login, /staff-login, dashboards)
│   │   ├── auth.py               OTP + admin login/logout
│   │   ├── client.py             all /api/client/* endpoints
│   │   ├── admin.py               all /api/admin/* endpoints (shared by Admin/Super/Primary,
│   │   │                          gated per-endpoint by require_permission)
│   │   └── primary_admin.py       /api/primary-admin/dashboard
│   └── services/
│       ├── allocation_service.py  FIFO allocation + capacity threshold checks
│       ├── notification_service.py  in-app + external notification routing
│       ├── notifiers.py            Email/WhatsApp/SMS provider abstraction (mock by default)
│       ├── payment_service.py      payment recording + stage progression
│       ├── project_service.py      stage creation + generation simulation
│       └── audit_service.py        audit log helper
├── templates/                    Jinja2 templates (base + per-role pages)
├── static/
│   ├── css/style.css              PV-cell design tokens, lifted from the original prototype
│   └── js/
│       ├── common.js               shared fetch/format helpers
│       ├── client.js                client dashboard SPA logic
│       └── console.js               Admin/Super Admin/Primary Admin console SPA logic
├── uploads/                       client document storage (created at runtime)
├── scripts/seed.py                database seed script
├── tests/test_core.py             pytest suite
├── requirements.txt
├── .env.example
└── suryasetu.db                   created on first run / seed
```

## API structure

All endpoints are under `/api/...` and documented live at `/docs`:

```
/api/auth           OTP send/verify, admin login/logout, /me
/api/client          onboarding, KYC, bill, documents, payments, generation,
                      services, tickets, notifications  (CLIENT role only, always
                      filtered to the authenticated client — a client can never
                      see another client's data)
/api/admin           dashboard, clients, projects, panels, allocation, stages,
                      payments, services, tickets, documents, staff management,
                      reports, audit logs, notifications
                      (shared by Admin / Super Admin / Primary Admin, with each
                      endpoint gated by require_permission(...) per the RBAC map)
/api/primary-admin    organizational dashboard (Primary Admin only)
```

## Role permissions, in short

- **Client** — sees and edits only their own data. Every client endpoint derives the
  client from the authenticated session; there is no client-supplied ID that bypasses this.
- **Admin** — day-to-day operations: manage clients, allocate panels, update stages, record
  payments, verify documents, handle services/tickets. Cannot manage Super Admins or view
  the Primary Admin's organizational dashboard.
- **Super Admin** — everything Admin can do, plus create/edit/remove Admins, full reports and
  audit log access. Cannot create or modify Super Admins or override the Primary Admin.
- **Primary Admin** — organizational control: create/manage both Admins and Super Admins,
  see every entity in the system, full audit trail. `role_has_permission()` in
  `app/permissions.py` grants Primary Admin every permission unconditionally.

`?role=super_admin` in a query string does nothing — role always comes from the JWT issued at
login, verified server-side on every request.

## FIFO panel allocation, explained

Each `Panel` row gets an `added_sequence` integer when it's added to a project (monotonically
increasing per project). `allocate_panels()`:

1. Locks the allocation critical section for the process.
2. Rejects immediately if the project is `FULL`, `CLOSED`, or `MAINTENANCE`.
3. Selects the N lowest-`added_sequence` panels with `status == AVAILABLE`.
4. If fewer than N are available, raises `AllocationError` — no partial allocation is ever
   committed.
5. Marks the selected panels `ALLOCATED`, links them to the client, updates the client's
   `ClientProject` aggregate, logs an audit entry, checks capacity thresholds, and commits
   atomically.

This guarantees the *oldest* available panels in a project are always allocated first,
exactly as required.

## Project capacity alerts, explained

`Project.utilization` = allocated panels ÷ total panels. After every allocation:

- `utilization == 1.0` (no panels left) → status `FULL`, notifies Admin + Super Admin +
  Primary Admin, and blocks all further allocation to that project.
- `utilization >= 0.90` (configurable via `CAPACITY_CRITICAL_THRESHOLD`) → status
  `NEAR_CAPACITY`, notifies Admin + Super Admin + Primary Admin.
- `utilization >= 0.80` (configurable via `CAPACITY_WARNING_THRESHOLD`) → notifies Admin +
  Super Admin + Primary Admin without changing status (so the project stays visible as
  "active but getting full").

Thresholds live in `app/config.py` and can be changed via environment variables without
touching code.

## Notification routing, explained

`app/services/notification_service.py` has one function per event type from the spec
(`notify_new_client`, `notify_first_payment`, `notify_project_capacity`,
`notify_client_question`, `notify_service_request`), each hard-coding the same recipient
rules as the original brief:

| Event | Recipients |
|---|---|
| New client registered | Admin, Super Admin |
| First payment | Admin, Super Admin |
| Capacity warning / critical / full | Admin, Super Admin, Primary Admin |
| Client question (ticket) | Admin, Super Admin |
| Service request | Admin, Super Admin |

Every notification is written to the in-app `Notification` table (visible in each role's
console) and, if the recipient has configured any `NotificationContact` rows (email / phone /
WhatsApp — manageable via `/api/admin/notification-contacts`), also dispatched through the
matching mock/real provider in `notifiers.py`.

## Security notes for anyone extending this

- Passwords are bcrypt-hashed (`passlib`); client accounts never get a password at all (OTP
  only).
- JWTs are short-lived (default 8 hours, configurable) and carried in an `httponly` cookie.
- File uploads are written under a per-client, per-document-type path with a sanitized
  filename — no path traversal from user input.
- Every mutation that matters (allocation, payments, stage changes, staff changes, document
  verification) writes an `AuditLog` row with the actor, so "who did what, when" is always
  answerable.
- This is a development build: the seeded passwords are printed in plaintext by `seed.py` and
  the `SECRET_KEY` in `.env.example` is a placeholder. Rotate both before deploying anywhere
  reachable outside your own machine.
