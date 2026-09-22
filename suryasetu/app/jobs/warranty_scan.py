"""Warranty expiry scan job.

Safe to run repeatedly: each panel is notified at most once while it remains
EXPIRING_SOON (deduped by existing WARRANTY_EXPIRING notifications).

Development:
  The FastAPI startup hook already runs a scan, and staff can click
  "Scan Expiring" in the warranty screen.

Production (cron / systemd timer / k8s CronJob), every 6 hours:
  cd /path/to/suryasetu && ENVIRONMENT=production python -m app.jobs.warranty_scan

Do not run overlapping instances against SQLite.
"""
import sys

from ..database import SessionLocal
from ..logging_config import logger
from ..services import warranty_service


def run() -> int:
    db = SessionLocal()
    try:
        n = warranty_service.scan_expiring_warranties(db)
        db.commit()
        logger.info("warranty_scan_complete", extra={"result": n})
        print(f"Warranty scan complete. Notified {n} expiring panel(s).")
        return n
    except Exception:
        db.rollback()
        logger.exception("warranty_scan_failed")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    try:
        run()
    except Exception:
        sys.exit(1)
