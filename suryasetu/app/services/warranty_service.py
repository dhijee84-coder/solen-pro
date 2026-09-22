"""Warranty status calculation, claim workflow, and expiry alerts."""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .. import models
from .audit_service import log_action
from . import notification_service


CLAIM_TRANSITIONS = {
    models.WarrantyClaimStatus.SUBMITTED: [
        models.WarrantyClaimStatus.UNDER_REVIEW,
        models.WarrantyClaimStatus.REJECTED,
        models.WarrantyClaimStatus.CLOSED,
    ],
    models.WarrantyClaimStatus.UNDER_REVIEW: [
        models.WarrantyClaimStatus.MORE_INFORMATION_REQUIRED,
        models.WarrantyClaimStatus.APPROVED,
        models.WarrantyClaimStatus.REJECTED,
    ],
    models.WarrantyClaimStatus.MORE_INFORMATION_REQUIRED: [
        models.WarrantyClaimStatus.UNDER_REVIEW,
        models.WarrantyClaimStatus.REJECTED,
        models.WarrantyClaimStatus.CLOSED,
    ],
    models.WarrantyClaimStatus.APPROVED: [
        models.WarrantyClaimStatus.REPLACEMENT_REQUIRED,
        models.WarrantyClaimStatus.REPAIRED,
        models.WarrantyClaimStatus.REPLACED,
        models.WarrantyClaimStatus.CLOSED,
    ],
    models.WarrantyClaimStatus.REPLACEMENT_REQUIRED: [
        models.WarrantyClaimStatus.REPLACED,
        models.WarrantyClaimStatus.CLOSED,
    ],
    models.WarrantyClaimStatus.REPAIRED: [models.WarrantyClaimStatus.CLOSED],
    models.WarrantyClaimStatus.REPLACED: [models.WarrantyClaimStatus.CLOSED],
    models.WarrantyClaimStatus.REJECTED: [models.WarrantyClaimStatus.CLOSED],
    models.WarrantyClaimStatus.CLOSED: [],
}


def get_expiring_days(db: Session) -> int:
    row = db.query(models.SystemSetting).filter(models.SystemSetting.key == "warranty_expiring_days").first()
    if row and str(row.value).isdigit():
        return int(row.value)
    return 90


def panel_warranty_status(panel: models.Panel, expiring_days: int = 90) -> str:
    return panel.computed_warranty_status(expiring_days)


def ensure_panel_warranty_dates(panel: models.Panel, install_date: str | None = None):
    if not panel.warranty_start_date:
        panel.warranty_start_date = install_date or panel.installation_date or datetime.utcnow().strftime("%Y-%m-%d")
    if not panel.warranty_end_date and panel.warranty_years:
        try:
            start = datetime.strptime(panel.warranty_start_date[:10], "%Y-%m-%d")
            end = start + timedelta(days=365 * panel.warranty_years)
            panel.warranty_end_date = end.strftime("%Y-%m-%d")
        except Exception:
            pass
    if not panel.warranty_provider:
        panel.warranty_provider = panel.manufacturer or "Manufacturer"
    if not panel.warranty_type:
        panel.warranty_type = "MANUFACTURER"


def create_claim(
    db: Session,
    panel: models.Panel,
    client: models.ClientProfile,
    issue_summary: str,
    description: str = "",
    date_discovered: str | None = None,
    contact_phone: str = "",
    contact_email: str = "",
) -> models.WarrantyClaim:
    claim = models.WarrantyClaim(
        panel_id=panel.id,
        client_id=client.id,
        issue_summary=issue_summary,
        description=description,
        date_discovered=date_discovered,
        contact_phone=contact_phone,
        contact_email=contact_email,
        status=models.WarrantyClaimStatus.SUBMITTED,
    )
    db.add(claim)
    db.flush()
    actor = client.user
    log_action(db, actor, "WARRANTY_CLAIM_SUBMITTED", entity_type="warranty_claim", entity_id=claim.id)
    title = "Warranty claim submitted"
    msg = f"{client.user.full_name if client.user else 'Client'} submitted a claim for panel {panel.serial_number}: {issue_summary}"
    for u in notification_service._admins_super_admins_and_primary(db):
        notification_service.notify_user(
            db, u, "WARRANTY", title, msg,
            related_entity="warranty_claim", related_entity_id=claim.id,
        )
    if client.user:
        notification_service.notify_user(
            db, client.user, "WARRANTY", "Warranty claim received",
            f"Claim {claim.id} for panel {panel.serial_number} has been submitted.",
            related_entity="warranty_claim", related_entity_id=claim.id,
        )
    return claim


def allowed_next_statuses(current: models.WarrantyClaimStatus):
    return CLAIM_TRANSITIONS.get(current, [])


def update_claim_status(
    db: Session,
    claim: models.WarrantyClaim,
    new_status: models.WarrantyClaimStatus,
    actor: models.User,
    notes: str = "",
):
    old = claim.status
    allowed = allowed_next_statuses(old)
    if new_status not in allowed:
        raise ValueError(
            f"Cannot move claim from {old.value} to {new_status.value}. "
            f"Allowed: {', '.join(s.value for s in allowed) or 'none'}."
        )
    claim.status = new_status
    if notes:
        stamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")
        claim.resolution_notes = ((claim.resolution_notes or "") + f"\n[{stamp}] {notes}").strip()
    claim.updated_at = datetime.utcnow()
    log_action(
        db, actor, "WARRANTY_CLAIM_UPDATED",
        entity_type="warranty_claim", entity_id=claim.id,
        old_value=old.value, new_value=new_status.value,
    )
    if claim.client and claim.client.user:
        notification_service.notify_user(
            db, claim.client.user, "WARRANTY",
            f"Warranty claim {new_status.value.replace('_', ' ').title()}",
            f"Your warranty claim {claim.id} is now {new_status.value.replace('_', ' ')}."
            + (f" Note: {notes}" if notes else ""),
            related_entity="warranty_claim", related_entity_id=claim.id,
        )


def scan_expiring_warranties(db: Session) -> int:
    """Notify once per panel when warranty is EXPIRING_SOON. Safe to run repeatedly."""
    exp_days = get_expiring_days(db)
    panels = db.query(models.Panel).filter(models.Panel.client_id.isnot(None)).all()
    sent = 0
    staff = notification_service._admins_super_admins_and_primary(db)
    for pan in panels:
        status = pan.computed_warranty_status(exp_days)
        if status != models.WarrantyStatus.EXPIRING_SOON.value:
            continue
        existing = db.query(models.Notification).filter(
            models.Notification.type == "WARRANTY_EXPIRING",
            models.Notification.related_entity == "panel",
            models.Notification.related_entity_id == pan.id,
        ).first()
        if existing:
            continue
        client = db.query(models.ClientProfile).filter(models.ClientProfile.id == pan.client_id).first()
        title = "Warranty expiring soon"
        msg = f"Panel {pan.serial_number} warranty ends on {pan.warranty_end_date}."
        if client and client.user:
            notification_service.notify_user(
                db, client.user, "WARRANTY_EXPIRING", title, msg,
                related_entity="panel", related_entity_id=pan.id,
            )
        for u in staff:
            notification_service.notify_user(
                db, u, "WARRANTY_EXPIRING", title,
                f"{client.user.full_name if client and client.user else pan.client_id}: {msg}",
                related_entity="panel", related_entity_id=pan.id,
            )
        sent += 1
    return sent
