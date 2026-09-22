# SuryaSetu — PostgreSQL migration path

SQLite is fully supported for local development and the live demo.
PostgreSQL is the recommended production database. No automatic migration
is forced; switch when you are ready.

## 1. Install the driver

```
pip install psycopg2-binary
```

(Not in `requirements.txt` so a SQLite-only install stays lightweight.)

## 2. Create the database

```
createuser suryasetu
createdb -O suryasetu suryasetu
```

## 3. Point the app at PostgreSQL

```
ENVIRONMENT=production
DATABASE_URL=postgresql+psycopg2://suryasetu:YOUR_PASSWORD@127.0.0.1:5432/suryasetu
```

On first start, SQLAlchemy `create_all` plus `ensure_indexes()` create the
schema and search indexes. For an existing production system, prefer a
proper migration tool (Alembic) before destructive changes.

## 4. Moving data from SQLite

There is no one-click converter shipped with the app. A typical path:

1. Take a SQLite backup (see [BACKUP.md](BACKUP.md)).
2. Start a fresh PostgreSQL schema (`create_all`).
3. Copy rows with a one-off script or `pgloader`:

```
pgloader sqlite:///suryasetu.db postgresql://suryasetu:pass@127.0.0.1/suryasetu
```

4. Copy the `uploads/` directory to `UPLOAD_DIR`.
5. Verify row counts and a staff login before switching DNS.

## 5. Concurrency

`allocation_service.allocate_panels` uses:

- SQLite: a process-wide threading lock (single worker only).
- PostgreSQL: `SELECT ... FOR UPDATE` on the project row, plus the same lock.

Run **one** uvicorn worker with SQLite. Multiple workers are safe only on
PostgreSQL (and still benefit from a reverse-proxy rate limiter).

## 6. Indexes

These are created automatically on startup (`app/database.py:ensure_indexes`):

- panels: client_id, project_id, status
- payments: client_id, status
- notifications: recipient, type+entity
- documents, tickets, claims, stages, generation, audit, enquiries

## 7. Do not

- Do not run `scripts/seed.py` against production (it drops all tables).
- Do not reuse the development `SECRET_KEY`.
- Do not expose PostgreSQL to the public internet.
