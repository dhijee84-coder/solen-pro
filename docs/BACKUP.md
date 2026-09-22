# SuryaSetu — backup and recovery

This is documentation only. Nothing here runs automatically or deletes data.

## What to back up

1. **Database** — all business data (users, projects, panels, payments, tickets, CMS, audit).
2. **Upload directory** — client documents, branding images, warranty attachments.
3. **Environment file** — `SECRET_KEY` and provider credentials (store in a secret manager, not next to the DB dump).

## SQLite (development / single-node)

While the app is idle or after a short pause:

```
mkdir -p backups
cp suryasetu.db backups/suryasetu-$(date +%Y%m%d-%H%M%S).db
cp -a uploads backups/uploads-$(date +%Y%m%d-%H%M%S)
```

SQLite also supports an online backup API if you cannot pause writes:

```
sqlite3 suryasetu.db ".backup 'backups/suryasetu-live.db'"
```

Restore (destructive — confirm before running):

```
# stop the app first
cp backups/suryasetu-YYYYMMDD-HHMMSS.db suryasetu.db
rsync -a backups/uploads-YYYYMMDD-HHMMSS/ uploads/
```

## PostgreSQL

Backup:

```
pg_dump -Fc -f backups/suryasetu-$(date +%Y%m%d).dump suryasetu
```

Restore (destructive — confirm before running):

```
pg_restore --clean --if-exists -d suryasetu backups/suryasetu-YYYYMMDD.dump
```

Also back up `UPLOAD_DIR` with the same timestamp.

## After restore

1. Confirm `GET /health/ready` returns `ready`.
2. Sign in as a known staff user.
3. Open a client record and download a document to confirm files and DB still match.
4. Optionally run `python -m app.jobs.warranty_scan` once.

## Retention

Keep at least 7 daily and 4 weekly copies off-box. Encrypt backups that leave the host.
