import hashlib
import math
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .. import models

STAGE_DEFS = [
    (1, "Sign-off installation", 15, "Capacity agreement and farm row assignment for purchased panels. No rooftop work."),
    (2, "Installation inspection", 10, "Farm layout check and electrical drawing approved for the allocated row on Solan land."),
    (3, "Installation material arrival", 30, "Modules, inverter, mounting and cabling delivered to the Solan farm with serial numbers logged."),
    (4, "Installation commission", 20, "Mounting, stringing, earthing and inverter commissioning on our farm. Panels start generating."),
    (5, "Grid line connectivity", 15, "Farm meter sealed and synchronisation approved. Energy is billed from generation."),
    (6, "Fully commissioned", 10, "Handover of generation rights, warranty documents and portal monitoring. Solan maintains the plant."),
]

TARIFF = 7.10   # Rs per unit avoided
CO2_PER_KWH = 0.71


def create_stages_for_client(db: Session, client_id: str):
    existing = db.query(models.ProjectStage).filter(models.ProjectStage.client_id == client_id).count()
    if existing:
        return
    for num, name, pct, _blurb in STAGE_DEFS:
        stage = models.ProjectStage(
            client_id=client_id, stage_number=num, stage_name=name, percentage=pct,
            status=models.StageStatus.IN_PROGRESS if num == 1 else models.StageStatus.NOT_STARTED,
        )
        db.add(stage)
    db.commit()


def _seeded_random(key: str):
    h = hashlib.sha256(key.encode()).hexdigest()
    seed_int = int(h[:8], 16)

    def rnd():
        nonlocal seed_int
        seed_int = (seed_int * 1103515245 + 12345) & 0x7FFFFFFF
        return (seed_int % 100000) / 100000

    return rnd


def day_yield_kwh(kw: float, d: date) -> float:
    r = _seeded_random(d.isoformat())
    season = [1.06, 1.10, 1.12, 1.08, .95, .74, .68, .72, .84, .90, .95, 1.00][d.month - 1]
    return round(kw * 4.35 * season * (0.62 + r() * 0.44), 2)


def simulate_generation_history(db: Session, project_id: str, client_id: str, kw: float, days: int = 90):
    """Backfill plausible daily generation so dashboards have data to show."""
    today = date.today()
    for i in range(days, -1, -1):
        d = today - timedelta(days=i)
        existing = db.query(models.GenerationRecord).filter(
            models.GenerationRecord.client_id == client_id, models.GenerationRecord.date == d.isoformat()
        ).first()
        if existing:
            continue
        gen = day_yield_kwh(kw, d)
        rec = models.GenerationRecord(
            project_id=project_id, client_id=client_id, date=d.isoformat(),
            generation_kwh=gen, allocated_generation_kwh=gen,
            peak_kw=round(kw * (0.78 + _seeded_random(d.isoformat() + "pk")() * 0.2), 2),
            co2_saved_kg=round(gen * CO2_PER_KWH, 2),
        )
        db.add(rec)
    db.commit()
