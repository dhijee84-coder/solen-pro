"""
FIFO panel allocation + project capacity alerting (spec sections 18-19, 46-49).

Concurrency note: SQLite does not give us SELECT ... FOR UPDATE row locking.
Two safeguards are used instead:
  1. A process-wide lock serializes the allocate() critical section so two
     concurrent admin requests in the same server process cannot race.
  2. Panel.status is re-checked and updated inside the same DB transaction
     that reads it, and committed atomically, so a partially-applied
     allocation can never be persisted.
For a multi-process production deployment this lock should be replaced with
a real row-level lock (e.g. Postgres `SELECT ... FOR UPDATE SKIP LOCKED`).
"""
import threading

from sqlalchemy.orm import Session

from .. import models
from ..config import settings
from . import notification_service
from .audit_service import log_action

_allocation_lock = threading.Lock()


class AllocationError(Exception):
    pass


def _check_capacity_alerts(db: Session, project: models.Project, actor: models.User):
    util = project.utilization
    if project.available_panels == 0 and project.total_panels > 0:
        if project.status != models.ProjectStatus.FULL:
            project.status = models.ProjectStatus.FULL
            notification_service.notify_project_capacity(db, project, "FULL")
    elif util >= settings.capacity_critical_threshold:
        if project.status != models.ProjectStatus.NEAR_CAPACITY:
            project.status = models.ProjectStatus.NEAR_CAPACITY
            notification_service.notify_project_capacity(db, project, "CRITICAL")
    elif util >= settings.capacity_warning_threshold:
        if project.status not in (models.ProjectStatus.NEAR_CAPACITY,):
            notification_service.notify_project_capacity(db, project, "WARNING")


def allocate_panels(db: Session, project_id: str, client_id: str, count: int, actor: models.User) -> list[models.Panel]:
    """Allocate `count` panels from `project_id` to `client_id` using strict FIFO
    (lowest added_sequence first), inside a serialized critical section."""
    if count <= 0:
        raise AllocationError("Panel count must be positive.")

    with _allocation_lock:
        project = db.query(models.Project).filter(models.Project.id == project_id).with_for_update(read=False).first() \
            if db.bind.dialect.name != "sqlite" else db.query(models.Project).filter(models.Project.id == project_id).first()
        if not project:
            raise AllocationError("Project not found.")
        if project.status in (models.ProjectStatus.FULL, models.ProjectStatus.CLOSED, models.ProjectStatus.MAINTENANCE):
            raise AllocationError(f"Project is {project.status.value} and cannot receive new allocations.")

        client = db.query(models.ClientProfile).filter(models.ClientProfile.id == client_id).first()
        if not client:
            raise AllocationError("Client not found.")

        # Only AVAILABLE panels, FIFO by added_sequence (section 18/48)
        candidates = (
            db.query(models.Panel)
            .filter(models.Panel.project_id == project_id, models.Panel.status == models.PanelStatus.AVAILABLE)
            .order_by(models.Panel.added_sequence.asc())
            .limit(count)
            .all()
        )
        if len(candidates) < count:
            raise AllocationError(
                f"Project has insufficient available panels: requested {count}, available {len(candidates)}."
            )

        for p in candidates:
            p.status = models.PanelStatus.ALLOCATED
            p.client_id = client_id

        cp = db.query(models.ClientProject).filter(models.ClientProject.client_id == client_id).first()
        capacity_added_kw = sum((p.watt_rating or 0) for p in candidates) / 1000.0
        if not cp:
            cp = models.ClientProject(
                client_id=client_id, project_id=project_id,
                allocated_panel_count=len(candidates), allocated_capacity_kw=capacity_added_kw,
            )
            db.add(cp)
        else:
            cp.allocated_panel_count += len(candidates)
            cp.allocated_capacity_kw += capacity_added_kw

        client.onboarding_stage = "PROJECT_ASSIGNED"

        log_action(
            db, actor, "PANEL_ALLOCATED", entity_type="project", entity_id=project_id,
            new_value=f"client={client_id} panels={[p.serial_number for p in candidates]}",
        )

        _check_capacity_alerts(db, project, actor)

        db.commit()
        for p in candidates:
            db.refresh(p)
        return candidates


def deallocate_panel(db: Session, panel_id: str, actor: models.User):
    with _allocation_lock:
        panel = db.query(models.Panel).filter(models.Panel.id == panel_id).first()
        if not panel:
            raise AllocationError("Panel not found.")
        old_client = panel.client_id
        panel.status = models.PanelStatus.AVAILABLE
        panel.client_id = None
        if old_client:
            cp = db.query(models.ClientProject).filter(models.ClientProject.client_id == old_client).first()
            if cp:
                cp.allocated_panel_count = max(0, cp.allocated_panel_count - 1)
                cp.allocated_capacity_kw = max(0.0, cp.allocated_capacity_kw - (panel.watt_rating or 0) / 1000.0)
        log_action(db, actor, "PANEL_DEALLOCATED", entity_type="panel", entity_id=panel_id, old_value=old_client or "")
        project = db.query(models.Project).filter(models.Project.id == panel.project_id).first()
        if project and project.status == models.ProjectStatus.FULL:
            project.status = models.ProjectStatus.NEAR_CAPACITY
        db.commit()
        return panel
