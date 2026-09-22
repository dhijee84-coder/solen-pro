from datetime import datetime, timedelta
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from .. import models, schemas
from ..database import get_db
from ..dependencies import require_roles, require_permission
from ..security import hash_password
from ..services import allocation_service, notification_service, project_service, payment_service
from ..services.allocation_service import AllocationError
from ..services.audit_service import log_action

router = APIRouter(prefix="/api/admin", tags=["admin"])

staff_roles = require_roles(models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN, models.RoleName.PRIMARY_ADMIN)
manage_roles = require_roles(models.RoleName.SUPER_ADMIN, models.RoleName.PRIMARY_ADMIN)


# ── dashboard ───────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_clients = db.query(func.count(models.ClientProfile.id)).scalar() or 0
    new_today = db.query(func.count(models.User.id)).filter(
        models.User.role == models.RoleName.CLIENT,
        models.User.created_at >= start_of_day,
    ).scalar() or 0
    active_projects = db.query(func.count(models.Project.id)).filter(models.Project.status == models.ProjectStatus.ACTIVE).scalar() or 0
    near_capacity = db.query(func.count(models.Project.id)).filter(models.Project.status == models.ProjectStatus.NEAR_CAPACITY).scalar() or 0
    full_projects = db.query(func.count(models.Project.id)).filter(models.Project.status == models.ProjectStatus.FULL).scalar() or 0
    panels_available = db.query(func.count(models.Panel.id)).filter(models.Panel.status == models.PanelStatus.AVAILABLE).scalar() or 0
    panels_allocated = db.query(func.count(models.Panel.id)).filter(
        models.Panel.status.in_([models.PanelStatus.ALLOCATED, models.PanelStatus.INSTALLED, models.PanelStatus.RESERVED])
    ).scalar() or 0
    pending_payments = db.query(func.count(models.Payment.id)).filter(models.Payment.status == models.PaymentStatus.PENDING).scalar() or 0
    todays_payments = db.query(func.count(models.Payment.id)).filter(
        models.Payment.status == models.PaymentStatus.SUCCESS,
        models.Payment.paid_at >= start_of_day,
    ).scalar() or 0
    open_tickets = db.query(func.count(models.SupportTicket.id)).filter(models.SupportTicket.status.in_(
        [models.TicketStatus.OPEN, models.TicketStatus.ASSIGNED, models.TicketStatus.IN_PROGRESS])).scalar() or 0
    pending_docs = db.query(func.count(models.Document.id)).filter(models.Document.status == models.DocumentStatus.UPLOADED).scalar() or 0
    pending_services = db.query(func.count(models.ClientServiceRequest.id)).filter(models.ClientServiceRequest.status.in_(
        [models.ServiceRequestStatus.REQUESTED, models.ServiceRequestStatus.UNDER_REVIEW])).scalar() or 0

    from ..services import warranty_service
    exp_days = warranty_service.get_expiring_days(db)
    allocated_panels = db.query(models.Panel).filter(models.Panel.client_id.isnot(None)).all()
    expiring_w = sum(1 for p in allocated_panels if p.computed_warranty_status(exp_days) == "EXPIRING_SOON")
    open_claims = db.query(func.count(models.WarrantyClaim.id)).filter(
        models.WarrantyClaim.status.notin_([models.WarrantyClaimStatus.CLOSED, models.WarrantyClaimStatus.REJECTED])
    ).scalar() or 0
    new_enquiries = db.query(func.count(models.ContactEnquiry.id)).filter(models.ContactEnquiry.status == models.EnquiryStatus.NEW).scalar() or 0

    recent_audit = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(15).all()

    return {
        "cards": {
            "total_clients": total_clients, "new_clients_today": new_today,
            "active_projects": active_projects, "projects_near_capacity": near_capacity,
            "projects_full": full_projects, "panels_available": panels_available,
            "panels_allocated": panels_allocated, "pending_payments": pending_payments,
            "todays_payments": todays_payments, "open_tickets": open_tickets,
            "pending_documents": pending_docs, "pending_service_requests": pending_services,
            "expiring_warranties": expiring_w, "open_warranty_claims": open_claims,
            "new_enquiries": new_enquiries,
        },
        "recent_activity": [{
            "action": a.action, "entity_type": a.entity_type, "entity_id": a.entity_id,
            "timestamp": a.timestamp.isoformat(),
        } for a in recent_audit],
    }


@router.get("/search")
def global_search(q: str = "", db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    q = (q or "").strip()
    if len(q) < 2:
        return {"clients": [], "projects": [], "panels": [], "tickets": [], "claims": []}
    like = f"%{q}%"
    clients = (
        db.query(models.ClientProfile)
        .join(models.User, models.ClientProfile.user_id == models.User.id)
        .filter(
            (models.User.full_name.ilike(like))
            | (models.User.phone.ilike(like))
            | (models.ClientProfile.id.ilike(like))
        )
        .limit(8)
        .all()
    )
    projects = db.query(models.Project).filter(
        (models.Project.project_name.ilike(like)) | (models.Project.project_code.ilike(like))
    ).limit(6).all()
    panels = db.query(models.Panel).filter(models.Panel.serial_number.ilike(like)).limit(8).all()
    tickets = db.query(models.SupportTicket).filter(models.SupportTicket.subject.ilike(like)).limit(6).all()
    claims = db.query(models.WarrantyClaim).filter(
        (models.WarrantyClaim.issue_summary.ilike(like)) | (models.WarrantyClaim.id.ilike(like))
    ).limit(6).all()
    return {
        "clients": [{"id": c.id, "name": c.user.full_name, "phone": c.user.phone} for c in clients],
        "projects": [{"id": p.id, "name": p.project_name, "code": p.project_code} for p in projects],
        "panels": [{"id": p.id, "serial": p.serial_number, "client_id": p.client_id} for p in panels],
        "tickets": [{"id": t.id, "subject": t.subject, "status": t.status.value} for t in tickets],
        "claims": [{"id": c.id, "issue": c.issue_summary, "status": c.status.value} for c in claims],
    }


# ── clients ─────────────────────────────────────────────────────────

def _client_summary(c: models.ClientProfile):
    cp = c.client_project
    last_payment = sorted(c.payments, key=lambda p: p.created_at, reverse=True)[:1]
    return {
        "id": c.id, "name": c.user.full_name, "phone": c.user.phone, "email": c.user.email,
        "registered_at": c.created_at.isoformat(), "kyc_status": c.kyc_status,
        "onboarding_stage": c.onboarding_stage,
        "project": cp.project.project_name if cp else None,
        "panels": cp.allocated_panel_count if cp else 0,
        "payment_status": last_payment[0].status.value if last_payment else "NONE",
        "is_active": c.user.is_active,
    }


@router.get("/clients")
def list_clients(q: str = "", limit: int = 200, offset: int = 0,
                 db: Session = Depends(get_db), user: models.User = Depends(require_permission("clients.view"))):
    query = (
        db.query(models.ClientProfile)
        .options(
            joinedload(models.ClientProfile.user),
            joinedload(models.ClientProfile.client_project).joinedload(models.ClientProject.project),
            joinedload(models.ClientProfile.payments),
        )
        .join(models.User, models.ClientProfile.user_id == models.User.id)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(
            (models.User.full_name.ilike(like)) | (models.User.phone.ilike(like)) |
            (models.User.email.ilike(like)) | (models.ClientProfile.id.ilike(like))
        )
    limit = min(max(int(limit or 200), 1), 500)
    offset = max(int(offset or 0), 0)
    clients = query.order_by(models.ClientProfile.created_at.desc()).offset(offset).limit(limit).all()
    return [_client_summary(c) for c in clients]


@router.get("/clients/{client_id}")
def client_detail(client_id: str, db: Session = Depends(get_db), user: models.User = Depends(require_permission("clients.view"))):
    c = db.query(models.ClientProfile).filter(models.ClientProfile.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found.")
    stages = db.query(models.ProjectStage).filter(models.ProjectStage.client_id == c.id).order_by(models.ProjectStage.stage_number).all()
    docs = db.query(models.Document).filter(models.Document.client_id == c.id).all()
    pays = db.query(models.Payment).filter(models.Payment.client_id == c.id).order_by(models.Payment.created_at.desc()).all()
    tickets = db.query(models.SupportTicket).filter(models.SupportTicket.client_id == c.id).all()
    services = db.query(models.ClientServiceRequest).filter(models.ClientServiceRequest.client_id == c.id).all()
    panels = db.query(models.Panel).filter(models.Panel.client_id == c.id).all()

    return {
        "profile": {
            "id": c.id, "name": c.user.full_name, "phone": c.user.phone, "email": c.user.email,
            "address": c.address, "city": c.city, "state": c.state, "pincode": c.pincode,
            "kyc_status": c.kyc_status, "pan_number": c.pan_number, "aadhaar_masked": c.aadhaar_masked,
            "onboarding_stage": c.onboarding_stage, "admin_notes": c.admin_notes,
            "assigned_admin_id": c.assigned_admin_id,
            "visibility": {k: getattr(c, k) for k in [
                "show_generation", "show_payments", "show_project", "show_panels",
                "show_documents", "show_services", "show_support", "show_notifications"]},
        },
        "electricity": None if not c.electricity_connection else {
            "rr_number": c.electricity_connection.rr_number, "discom": c.electricity_connection.discom,
            "avg_monthly_units": c.electricity_connection.avg_monthly_units,
            "proposed_kw": c.electricity_connection.proposed_kw,
            "system_cost": c.electricity_connection.system_cost,
            "payable_amount": c.electricity_connection.payable_amount,
        },
        "project": None if not c.client_project else {
            "project_name": c.client_project.project.project_name,
            "project_code": c.client_project.project.project_code,
            "allocated_panels": c.client_project.allocated_panel_count,
            "allocated_capacity_kw": c.client_project.allocated_capacity_kw,
        },
        "panels": [{"id": p.id, "serial_number": p.serial_number, "status": p.status.value} for p in panels],
        "stages": [{
            "id": s.id, "number": s.stage_number, "name": s.stage_name, "status": s.status.value,
            "percentage": s.percentage, "payment_status": s.payment_status,
        } for s in stages],
        "documents": [{"id": d.id, "type": d.document_type.value, "status": d.status.value, "filename": d.original_filename} for d in docs],
        "payments": [{"id": p.id, "amount": p.amount, "status": p.status.value, "method": p.payment_method, "created_at": p.created_at.isoformat()} for p in pays],
        "tickets": [{"id": t.id, "subject": t.subject, "status": t.status.value} for t in tickets],
        "service_requests": [{"id": s.id, "service": s.service.name, "status": s.status.value} for s in services],
    }


@router.put("/clients/{client_id}")
def update_client(client_id: str, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(require_permission("clients.edit"))):
    c = db.query(models.ClientProfile).filter(models.ClientProfile.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found.")
    editable = ["address", "city", "state", "pincode", "admin_notes", "assigned_admin_id"]
    old = {f: getattr(c, f) for f in editable}
    for f in editable:
        if f in payload:
            setattr(c, f, payload[f])
    visibility_fields = ["show_generation", "show_payments", "show_project", "show_panels",
                          "show_documents", "show_services", "show_support", "show_notifications"]
    for f in visibility_fields:
        if f in payload:
            setattr(c, f, bool(payload[f]))
    log_action(db, user, "CLIENT_UPDATED", entity_type="client", entity_id=c.id, old_value=str(old), new_value=str(payload))
    db.commit()
    return {"success": True}


@router.post("/clients/{client_id}/verify-document/{document_id}")
def verify_document(client_id: str, document_id: str, approve: bool = True, db: Session = Depends(get_db),
                     user: models.User = Depends(require_permission("documents.verify"))):
    doc = db.query(models.Document).filter(models.Document.id == document_id, models.Document.client_id == client_id).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    doc.status = models.DocumentStatus.VERIFIED if approve else models.DocumentStatus.REJECTED
    doc.verified_by = user.id
    doc.verified_at = datetime.utcnow()
    log_action(db, user, "DOCUMENT_VERIFIED", entity_type="document", entity_id=doc.id, new_value=doc.status.value)
    db.commit()
    return {"success": True, "status": doc.status.value}


# ── projects ────────────────────────────────────────────────────────

def _project_dict(p: models.Project):
    return {
        "id": p.id, "code": p.project_code, "name": p.project_name, "site_name": p.site_name,
        "location": p.location, "capacity_kw": p.capacity_kw, "total_panels": p.total_panels,
        "allocated_panels": p.allocated_panels, "available_panels": p.available_panels,
        "utilization": round(p.utilization * 100, 1), "status": p.status.value,
        "is_public": bool(p.is_public), "public_description": p.public_description or "",
    }


@router.get("/projects")
def list_projects(db: Session = Depends(get_db), user: models.User = Depends(require_permission("projects.view"))):
    return [_project_dict(p) for p in db.query(models.Project).order_by(models.Project.created_at.desc()).all()]


@router.post("/projects")
def create_project(payload: schemas.ProjectCreateIn, db: Session = Depends(get_db), user: models.User = Depends(require_permission("projects.create"))):
    if db.query(models.Project).filter(models.Project.project_code == payload.project_code).first():
        raise HTTPException(400, "Project code already exists.")
    p = models.Project(**payload.model_dump(), status=models.ProjectStatus.PLANNING)
    db.add(p)
    db.flush()
    log_action(db, user, "PROJECT_CREATED", entity_type="project", entity_id=p.id, new_value=p.project_name)
    db.commit()
    return _project_dict(p)


@router.put("/projects/{project_id}")
def update_project(project_id: str, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(require_permission("projects.edit"))):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found.")
    for f in ["project_name", "site_name", "location", "address", "commissioning_date"]:
        if f in payload:
            setattr(p, f, payload[f])
    if "status" in payload and payload["status"] in models.ProjectStatus.__members__:
        p.status = models.ProjectStatus[payload["status"]]
    log_action(db, user, "PROJECT_UPDATED", entity_type="project", entity_id=p.id, new_value=str(payload))
    db.commit()
    return _project_dict(p)


@router.post("/projects/{project_id}/panels")
def add_panels(project_id: str, payload: schemas.PanelBulkAddIn, db: Session = Depends(get_db),
               user: models.User = Depends(require_permission("panels.create"))):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found.")
    max_seq = db.query(models.Panel).filter(models.Panel.project_id == project_id).count()
    existing_serials = db.query(models.Panel).filter(models.Panel.project_id == project_id).count()
    created = []
    for i in range(payload.count):
        seq = max_seq + i + 1
        serial = f"{p.project_code}-P{existing_serials + i + 1:05d}"
        panel = models.Panel(
            serial_number=serial, project_id=project_id, manufacturer=payload.manufacturer,
            model=payload.model, watt_rating=payload.watt_rating, added_sequence=seq,
            status=models.PanelStatus.AVAILABLE,
        )
        db.add(panel)
        created.append(serial)
    p.total_panels += payload.count
    p.capacity_kw += payload.count * payload.watt_rating / 1000.0
    if p.status == models.ProjectStatus.PLANNING:
        p.status = models.ProjectStatus.ACTIVE
    log_action(db, user, "PROJECT_UPDATED", entity_type="project", entity_id=p.id, new_value=f"+{payload.count} panels")
    db.commit()
    return {"success": True, "added": len(created), "first_serial": created[0] if created else None, "last_serial": created[-1] if created else None}


@router.get("/panels")
def list_panels(project_id: str = None, status: str = None, db: Session = Depends(get_db),
                 user: models.User = Depends(require_permission("panels.view"))):
    q = db.query(models.Panel)
    if project_id:
        q = q.filter(models.Panel.project_id == project_id)
    if status:
        q = q.filter(models.Panel.status == status)
    panels = q.order_by(models.Panel.added_sequence).limit(500).all()
    return [{
        "id": x.id, "serial_number": x.serial_number, "project_id": x.project_id,
        "status": x.status.value, "client_id": x.client_id, "watt_rating": x.watt_rating,
        "added_sequence": x.added_sequence,
    } for x in panels]


@router.post("/allocate")
def allocate(payload: schemas.AllocateIn, db: Session = Depends(get_db), user: models.User = Depends(require_permission("panels.allocate"))):
    try:
        panels = allocation_service.allocate_panels(db, payload.project_id, payload.client_id, payload.panel_count, user)
    except AllocationError as e:
        raise HTTPException(400, str(e))
    return {
        "success": True,
        "allocated_serials": [p.serial_number for p in panels],
        "count": len(panels),
    }


@router.get("/allocate/preview")
def allocate_preview(project_id: str, count: int, db: Session = Depends(get_db), user: models.User = Depends(require_permission("panels.allocate"))):
    """FIFO preview shown to the admin before confirming (spec section 47)."""
    candidates = (
        db.query(models.Panel)
        .filter(models.Panel.project_id == project_id, models.Panel.status == models.PanelStatus.AVAILABLE)
        .order_by(models.Panel.added_sequence.asc())
        .limit(count)
        .all()
    )
    return {
        "requested": count, "available_shown": len(candidates),
        "serials": [p.serial_number for p in candidates],
        "sufficient": len(candidates) >= count,
    }


@router.post("/panels/{panel_id}/deallocate")
def deallocate(panel_id: str, db: Session = Depends(get_db), user: models.User = Depends(require_permission("panels.allocate"))):
    try:
        panel = allocation_service.deallocate_panel(db, panel_id, user)
    except AllocationError as e:
        raise HTTPException(400, str(e))
    return {"success": True, "panel_id": panel.id}


@router.post("/clients/{client_id}/assign-project")
def assign_project_and_provision(client_id: str, project_id: str, panel_count: int,
                                  db: Session = Depends(get_db), user: models.User = Depends(require_permission("panels.allocate"))):
    """Convenience endpoint: allocate panels, create the six stages, and backfill generation history."""
    try:
        allocation_service.allocate_panels(db, project_id, client_id, panel_count, user)
    except AllocationError as e:
        raise HTTPException(400, str(e))
    project_service.create_stages_for_client(db, client_id)
    client = db.query(models.ClientProfile).filter(models.ClientProfile.id == client_id).first()
    kw = client.electricity_connection.proposed_kw if client.electricity_connection else panel_count * 0.4
    project_service.simulate_generation_history(db, project_id, client_id, kw)
    return {"success": True}


# ── stages ──────────────────────────────────────────────────────────

@router.put("/stages/{stage_id}")
def update_stage(stage_id: str, payload: schemas.StageUpdateIn, db: Session = Depends(get_db),
                  user: models.User = Depends(require_permission("clients.edit"))):
    s = db.query(models.ProjectStage).filter(models.ProjectStage.id == stage_id).first()
    if not s:
        raise HTTPException(404, "Stage not found.")
    if payload.status not in models.StageStatus.__members__:
        raise HTTPException(400, "Invalid stage status.")
    old_status = s.status.value
    s.status = models.StageStatus[payload.status]
    if payload.notes is not None:
        s.notes = payload.notes
    if s.status == models.StageStatus.COMPLETED and not s.completed_at:
        s.completed_at = datetime.utcnow()
        s.completed_by = user.id
    if s.status == models.StageStatus.PAYMENT_DUE:
        s.payment_status = "DUE"
    log_action(db, user, "STAGE_UPDATED", entity_type="stage", entity_id=s.id, old_value=old_status, new_value=s.status.value)
    db.commit()
    return {"success": True}


# ── payments ────────────────────────────────────────────────────────

@router.get("/payments")
def list_all_payments(status: str = None, db: Session = Depends(get_db), user: models.User = Depends(require_permission("payments.view"))):
    q = db.query(models.Payment)
    if status:
        q = q.filter(models.Payment.status == status)
    pays = q.order_by(models.Payment.created_at.desc()).limit(200).all()
    return [{
        "id": p.id, "client_id": p.client_id, "client_name": p.client.user.full_name,
        "amount": p.amount, "status": p.status.value, "method": p.payment_method,
        "created_at": p.created_at.isoformat(), "is_first_payment": p.is_first_payment,
    } for p in pays]


@router.post("/clients/{client_id}/payments")
def record_payment_for_client(client_id: str, payload: schemas.PaymentIn, db: Session = Depends(get_db),
                               user: models.User = Depends(require_permission("payments.create"))):
    c = db.query(models.ClientProfile).filter(models.ClientProfile.id == client_id).first()
    if not c:
        raise HTTPException(404, "Client not found.")
    payment = payment_service.record_payment(db, c, payload.amount, payload.method, user, stage_id=payload.stage_id, service_id=payload.service_id)
    return {"success": True, "payment_id": payment.id, "txn": payment.transaction_reference}


# ── services & tickets ─────────────────────────────────────────────

@router.get("/services")
def list_services(db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    return [{"id": s.id, "name": s.name, "description": s.description, "base_price": s.base_price, "is_active": s.is_active}
            for s in db.query(models.Service).all()]


@router.post("/services")
def create_service(payload: schemas.ServiceCreateIn, db: Session = Depends(get_db), user: models.User = Depends(require_permission("clients.services.manage"))):
    s = models.Service(**payload.model_dump())
    db.add(s)
    log_action(db, user, "SERVICE_CREATED", entity_type="service", entity_id=s.name, new_value=payload.name)
    db.commit()
    return {"success": True, "id": s.id}


@router.get("/service-requests")
def list_service_requests(status: str = None, db: Session = Depends(get_db), user: models.User = Depends(require_permission("clients.services.view"))):
    q = db.query(models.ClientServiceRequest)
    if status:
        q = q.filter(models.ClientServiceRequest.status == status)
    reqs = q.order_by(models.ClientServiceRequest.created_at.desc()).all()
    return [{
        "id": r.id, "client_id": r.client_id, "client_name": r.client.user.full_name,
        "service": r.service.name, "status": r.status.value, "quoted_price": r.quoted_price,
        "created_at": r.created_at.isoformat(),
    } for r in reqs]


@router.put("/service-requests/{request_id}")
def update_service_request(request_id: str, payload: schemas.ServiceRequestUpdateIn, db: Session = Depends(get_db),
                            user: models.User = Depends(require_permission("clients.services.manage"))):
    r = db.query(models.ClientServiceRequest).filter(models.ClientServiceRequest.id == request_id).first()
    if not r:
        raise HTTPException(404, "Service request not found.")
    if payload.status not in models.ServiceRequestStatus.__members__:
        raise HTTPException(400, "Invalid status.")
    r.status = models.ServiceRequestStatus[payload.status]
    if payload.quoted_price is not None:
        r.quoted_price = payload.quoted_price
    if payload.notes is not None:
        r.notes = payload.notes
    r.assigned_admin_id = user.id
    log_action(db, user, "SERVICE_REQUESTED", entity_type="service_request", entity_id=r.id, new_value=r.status.value)
    db.commit()
    return {"success": True}


@router.get("/tickets")
def list_tickets(status: str = None, db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    q = db.query(models.SupportTicket)
    if status:
        q = q.filter(models.SupportTicket.status == status)
    ts = q.order_by(models.SupportTicket.created_at.desc()).all()
    return [{
        "id": t.id, "client_id": t.client_id, "client_name": t.client.user.full_name,
        "subject": t.subject, "status": t.status.value, "priority": t.priority,
        "category": t.category, "description": t.description,
        "created_at": t.created_at.isoformat(),
    } for t in ts]


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str, db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    t = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found.")
    msgs = db.query(models.TicketMessage).filter(models.TicketMessage.ticket_id == t.id).order_by(models.TicketMessage.created_at).all()
    return {
        "id": t.id, "client_id": t.client_id, "client_name": t.client.user.full_name,
        "subject": t.subject, "status": t.status.value, "priority": t.priority,
        "category": t.category, "description": t.description,
        "created_at": t.created_at.isoformat(),
        "messages": [{
            "id": m.id, "sender_user_id": m.sender_user_id, "message": m.message,
            "created_at": m.created_at.isoformat(),
            "mine": m.sender_user_id == user.id,
        } for m in msgs],
    }


@router.post("/tickets/{ticket_id}/messages")
def ticket_reply(ticket_id: str, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    t = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found.")
    msg = (payload.get("message") or "").strip()
    if not msg:
        raise HTTPException(400, "Message required.")
    db.add(models.TicketMessage(ticket_id=t.id, sender_user_id=user.id, message=msg))
    if t.status in (models.TicketStatus.OPEN, models.TicketStatus.WAITING_FOR_CLIENT):
        t.status = models.TicketStatus.IN_PROGRESS
    db.commit()
    return {"success": True}


@router.put("/tickets/{ticket_id}")
def update_ticket(ticket_id: str, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    t = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id).first()
    if not t:
        raise HTTPException(404, "Ticket not found.")
    if "status" in payload and payload["status"] in models.TicketStatus.__members__:
        t.status = models.TicketStatus[payload["status"]]
    if "assigned_admin_id" in payload:
        t.assigned_admin_id = payload["assigned_admin_id"]
    db.commit()
    return {"success": True}


# ── documents (admin-wide) ────────────────────────────────────────

@router.get("/documents")
def list_all_documents(status: str = None, db: Session = Depends(get_db), user: models.User = Depends(require_permission("documents.view"))):
    q = db.query(models.Document)
    if status:
        q = q.filter(models.Document.status == status)
    docs = q.order_by(models.Document.uploaded_at.desc()).limit(200).all()
    return [{
        "id": d.id, "client_id": d.client_id, "client_name": d.client.user.full_name,
        "type": d.document_type.value, "status": d.status.value, "filename": d.original_filename,
        "uploaded_at": d.uploaded_at.isoformat(),
    } for d in docs]


@router.get("/documents/{document_id}/file")
def download_document(document_id: str, db: Session = Depends(get_db),
                      user: models.User = Depends(require_permission("documents.view"))):
    doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    from ..services.storage import assert_under_upload_dir
    path = assert_under_upload_dir(doc.file_path)
    if not os.path.isfile(path):
        raise HTTPException(404, "File is no longer available.")
    return FileResponse(
        path,
        filename=doc.original_filename or doc.stored_filename,
        media_type=doc.mime_type or "application/octet-stream",
    )


# ── notifications ───────────────────────────────────────────────────

@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    ns = db.query(models.Notification).filter(models.Notification.recipient_user_id == user.id).order_by(models.Notification.created_at.desc()).limit(80).all()
    return [{
        "id": n.id, "type": n.type, "title": n.title, "message": n.message,
        "priority": n.priority, "is_read": n.is_read, "created_at": n.created_at.isoformat(),
        "related_entity": n.related_entity, "related_entity_id": n.related_entity_id,
    } for n in ns]


@router.post("/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    n = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.recipient_user_id == user.id).first()
    if not n:
        raise HTTPException(404, "Notification not found.")
    n.is_read = True
    db.commit()
    return {"success": True}


@router.get("/notification-contacts")
def list_contacts(db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    cs = db.query(models.NotificationContact).filter(models.NotificationContact.user_id == user.id).all()
    return [{"id": c.id, "type": c.type.value, "value": c.value, "label": c.label, "is_active": c.is_active} for c in cs]


@router.post("/notification-contacts")
def add_contact(payload: schemas.ContactAddIn, db: Session = Depends(get_db), user: models.User = Depends(staff_roles)):
    if payload.type not in models.ContactType.__members__:
        raise HTTPException(400, "Invalid contact type.")
    c = models.NotificationContact(user_id=user.id, type=models.ContactType[payload.type], value=payload.value, label=payload.label)
    db.add(c)
    db.commit()
    return {"success": True, "id": c.id}


# ── admin management (Super Admin + Primary Admin only) ─────────────

@router.get("/staff")
def list_staff(db: Session = Depends(get_db), user: models.User = Depends(manage_roles)):
    staff = db.query(models.User).filter(models.User.role.in_([models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN])).all()
    return [{"id": s.id, "name": s.full_name, "username": s.username, "role": s.role.value, "is_active": s.is_active} for s in staff]


@router.post("/staff")
def create_staff(payload: schemas.AdminCreateIn, db: Session = Depends(get_db), user: models.User = Depends(manage_roles)):
    if payload.role not in ("ADMIN", "SUPER_ADMIN"):
        raise HTTPException(400, "Role must be ADMIN or SUPER_ADMIN.")
    if payload.role == "SUPER_ADMIN" and user.role != models.RoleName.PRIMARY_ADMIN:
        raise HTTPException(403, "Only the Primary Admin can create Super Admins.")
    if db.query(models.User).filter(models.User.username == payload.username).first():
        raise HTTPException(400, "Username already taken.")
    s = models.User(
        role=models.RoleName[payload.role], full_name=payload.full_name, username=payload.username,
        email=payload.email, hashed_password=hash_password(payload.password), created_by=user.id,
    )
    db.add(s)
    db.flush()
    log_action(db, user, "ADMIN_CREATED" if payload.role == "ADMIN" else "ROLE_CHANGED", entity_type="user", entity_id=s.id, new_value=payload.role)
    db.commit()
    return {"success": True, "id": s.id}


@router.put("/staff/{staff_id}")
def update_staff(staff_id: str, payload: dict, db: Session = Depends(get_db), user: models.User = Depends(manage_roles)):
    s = db.query(models.User).filter(models.User.id == staff_id).first()
    if not s or s.role not in (models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN):
        raise HTTPException(404, "Staff member not found.")
    if s.role == models.RoleName.SUPER_ADMIN and user.role != models.RoleName.PRIMARY_ADMIN:
        raise HTTPException(403, "Only the Primary Admin can modify Super Admins.")
    if "full_name" in payload:
        s.full_name = payload["full_name"]
    if "is_active" in payload:
        s.is_active = bool(payload["is_active"])
    log_action(db, user, "ADMIN_EDITED" if s.role == models.RoleName.ADMIN else "ROLE_CHANGED",
               entity_type="user", entity_id=s.id, new_value=str(payload))
    db.commit()
    return {"success": True}


@router.delete("/staff/{staff_id}")
def remove_staff(staff_id: str, db: Session = Depends(get_db), user: models.User = Depends(manage_roles)):
    s = db.query(models.User).filter(models.User.id == staff_id).first()
    if not s or s.role not in (models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN):
        raise HTTPException(404, "Staff member not found.")
    if s.role == models.RoleName.SUPER_ADMIN and user.role != models.RoleName.PRIMARY_ADMIN:
        raise HTTPException(403, "Only the Primary Admin can remove Super Admins.")
    s.is_active = False
    log_action(db, user, "ADMIN_REMOVED" if s.role == models.RoleName.ADMIN else "ROLE_CHANGED",
               entity_type="user", entity_id=s.id, new_value="deactivated")
    db.commit()
    return {"success": True}


# ── reports ─────────────────────────────────────────────────────────

@router.get("/reports/summary")
def reports_summary(db: Session = Depends(get_db), user: models.User = Depends(require_permission("reports.view"))):
    revenue_sum = db.query(func.coalesce(func.sum(models.Payment.amount), 0)).filter(
        models.Payment.status == models.PaymentStatus.SUCCESS
    ).scalar() or 0
    total_payments = db.query(func.count(models.Payment.id)).filter(
        models.Payment.status == models.PaymentStatus.SUCCESS
    ).scalar() or 0
    projects = db.query(models.Project).all()
    return {
        "total_revenue": float(revenue_sum),
        "total_payments": total_payments,
        "total_clients": db.query(func.count(models.ClientProfile.id)).scalar() or 0,
        "project_utilization": [{"project": p.project_name, "utilization_pct": round(p.utilization * 100, 1)} for p in projects],
    }


# ── audit log ───────────────────────────────────────────────────────

@router.get("/audit-logs")
def audit_logs(db: Session = Depends(get_db), user: models.User = Depends(require_permission("audit_logs.view"))):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(300).all()
    return [{
        "id": a.id, "actor_user_id": a.actor_user_id, "action": a.action,
        "entity_type": a.entity_type, "entity_id": a.entity_id,
        "new_value": a.new_value, "timestamp": a.timestamp.isoformat(),
    } for a in logs]


# ── CSV exports ─────────────────────────────────────────────────────

from ..services.export_service import to_csv, filename as csv_filename
from ..services import warranty_service
from ..permissions import permission_matrix, ALL_PERMISSIONS, ROLE_PERMISSIONS
from ..rate_limit import limiter
from ..config import settings


@router.get("/export/clients", dependencies=[Depends(limiter("export", settings.rate_limit_export))])
def export_clients(db: Session = Depends(get_db), user: models.User = Depends(require_permission("reports.export"))):
    clients = db.query(models.ClientProfile).all()
    headers = ["id", "name", "phone", "email", "city", "kyc_status", "onboarding_stage", "created_at"]
    rows = []
    for c in clients:
        u = c.user
        rows.append([c.id, u.full_name if u else "", u.phone if u else "", u.email if u else "",
                     c.city, c.kyc_status, c.onboarding_stage, c.created_at.isoformat() if c.created_at else ""])
    log_action(db, user, "EXPORT_CSV", entity_type="clients", new_value=str(len(rows)))
    db.commit()
    content = to_csv(headers, rows)
    return StreamingResponse(iter([content]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{csv_filename("clients")}"'})


@router.get("/export/payments", dependencies=[Depends(limiter("export", settings.rate_limit_export))])
def export_payments(db: Session = Depends(get_db), user: models.User = Depends(require_permission("reports.export"))):
    payments = db.query(models.Payment).order_by(models.Payment.created_at.desc()).limit(5000).all()
    headers = ["id", "client_id", "amount", "currency", "method", "status", "txn", "paid_at", "created_at"]
    rows = [[p.id, p.client_id, p.amount, p.currency, p.payment_method, p.status.value if p.status else "",
             p.transaction_reference or "", p.paid_at.isoformat() if p.paid_at else "",
             p.created_at.isoformat() if p.created_at else ""] for p in payments]
    log_action(db, user, "EXPORT_CSV", entity_type="payments", new_value=str(len(rows)))
    db.commit()
    content = to_csv(headers, rows)
    return StreamingResponse(iter([content]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{csv_filename("payments")}"'})


@router.get("/export/panels", dependencies=[Depends(limiter("export", settings.rate_limit_export))])
def export_panels(db: Session = Depends(get_db), user: models.User = Depends(require_permission("reports.export"))):
    exp_days = warranty_service.get_expiring_days(db)
    panels = db.query(models.Panel).order_by(models.Panel.added_sequence).limit(10000).all()
    headers = ["id", "serial", "project_id", "manufacturer", "model", "watt", "status", "client_id",
               "install_date", "warranty_start", "warranty_end", "warranty_status", "warranty_years"]
    rows = []
    for p in panels:
        rows.append([
            p.id, p.serial_number, p.project_id, p.manufacturer, p.model, p.watt_rating,
            p.status.value if p.status else "", p.client_id or "",
            p.installation_date or "", p.warranty_start_date or "", p.warranty_end_date or "",
            p.computed_warranty_status(exp_days), p.warranty_years or "",
        ])
    log_action(db, user, "EXPORT_CSV", entity_type="panels", new_value=str(len(rows)))
    db.commit()
    content = to_csv(headers, rows)
    return StreamingResponse(iter([content]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{csv_filename("panels")}"'})


@router.get("/export/warranty-claims", dependencies=[Depends(limiter("export", settings.rate_limit_export))])
def export_warranty_claims(db: Session = Depends(get_db), user: models.User = Depends(require_permission("reports.export"))):
    claims = db.query(models.WarrantyClaim).order_by(models.WarrantyClaim.created_at.desc()).limit(5000).all()
    headers = ["id", "panel_id", "client_id", "issue", "status", "date_discovered", "created_at"]
    rows = [[c.id, c.panel_id, c.client_id, c.issue_summary, c.status.value if c.status else "",
             c.date_discovered or "", c.created_at.isoformat() if c.created_at else ""] for c in claims]
    log_action(db, user, "EXPORT_CSV", entity_type="warranty_claims", new_value=str(len(rows)))
    db.commit()
    content = to_csv(headers, rows)
    return StreamingResponse(iter([content]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{csv_filename("warranty_claims")}"'})


@router.get("/export/audit-logs", dependencies=[Depends(limiter("export", settings.rate_limit_export))])
def export_audit(db: Session = Depends(get_db), user: models.User = Depends(require_permission("audit_logs.view"))):
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(5000).all()
    headers = ["id", "actor", "action", "entity_type", "entity_id", "new_value", "timestamp"]
    rows = [[a.id, a.actor_user_id or "", a.action, a.entity_type, a.entity_id, a.new_value,
             a.timestamp.isoformat() if a.timestamp else ""] for a in logs]
    log_action(db, user, "EXPORT_CSV", entity_type="audit_logs", new_value=str(len(rows)))
    db.commit()
    content = to_csv(headers, rows)
    return StreamingResponse(iter([content]), media_type="text/csv",
                             headers={"Content-Disposition": f'attachment; filename="{csv_filename("audit_logs")}"'})


# ── warranty ────────────────────────────────────────────────────────

@router.get("/warranty/panels")
def warranty_panels(status: str = None, db: Session = Depends(get_db),
                    user: models.User = Depends(require_permission("warranty.view"))):
    exp_days = warranty_service.get_expiring_days(db)
    panels = db.query(models.Panel).filter(models.Panel.client_id.isnot(None)).limit(2000).all()
    out = []
    for p in panels:
        ws = p.computed_warranty_status(exp_days)
        if status and ws != status:
            continue
        out.append({
            "id": p.id, "serial": p.serial_number, "manufacturer": p.manufacturer,
            "model": p.model, "client_id": p.client_id, "project_id": p.project_id,
            "warranty_start": p.warranty_start_date, "warranty_end": p.warranty_end_date,
            "warranty_status": ws, "warranty_years": p.warranty_years,
            "warranty_type": p.warranty_type, "warranty_provider": p.warranty_provider,
        })
    return out


@router.get("/warranty/claims")
def list_claims(status: str = None, db: Session = Depends(get_db),
                user: models.User = Depends(require_permission("warranty.view"))):
    q = db.query(models.WarrantyClaim)
    if status:
        try:
            q = q.filter(models.WarrantyClaim.status == models.WarrantyClaimStatus(status))
        except ValueError:
            pass
    claims = q.order_by(models.WarrantyClaim.created_at.desc()).limit(500).all()
    out = []
    for c in claims:
        panel = c.panel
        client = c.client
        out.append({
            "id": c.id, "panel_id": c.panel_id, "client_id": c.client_id,
            "panel_serial": panel.serial_number if panel else "",
            "manufacturer": panel.manufacturer if panel else "",
            "project_id": panel.project_id if panel else "",
            "client_name": client.user.full_name if client and client.user else "",
            "issue": c.issue_summary, "description": c.description,
            "status": c.status.value if c.status else "", "date_discovered": c.date_discovered,
            "created_at": c.created_at.isoformat() if c.created_at else "",
            "updated_at": c.updated_at.isoformat() if c.updated_at else "",
            "resolution_notes": c.resolution_notes or "",
            "allowed_next": [s.value for s in warranty_service.allowed_next_statuses(c.status)],
        })
    return out


@router.get("/warranty/claims/{claim_id}")
def claim_detail(claim_id: str, db: Session = Depends(get_db),
                 user: models.User = Depends(require_permission("warranty.view"))):
    c = db.query(models.WarrantyClaim).filter(models.WarrantyClaim.id == claim_id).first()
    if not c:
        raise HTTPException(404, "Claim not found.")
    panel = c.panel
    client = c.client
    exp_days = warranty_service.get_expiring_days(db)
    return {
        "id": c.id, "panel_id": c.panel_id, "client_id": c.client_id,
        "panel_serial": panel.serial_number if panel else "",
        "manufacturer": panel.manufacturer if panel else "",
        "model": panel.model if panel else "",
        "warranty_status": panel.computed_warranty_status(exp_days) if panel else "",
        "warranty_end": panel.warranty_end_date if panel else "",
        "project_id": panel.project_id if panel else "",
        "client_name": client.user.full_name if client and client.user else "",
        "client_phone": client.user.phone if client and client.user else "",
        "issue": c.issue_summary, "description": c.description,
        "status": c.status.value if c.status else "", "date_discovered": c.date_discovered,
        "contact_phone": c.contact_phone, "contact_email": c.contact_email,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
        "resolution_notes": c.resolution_notes or "",
        "allowed_next": [s.value for s in warranty_service.allowed_next_statuses(c.status)],
    }


@router.post("/warranty/claims/{claim_id}/status")
def update_claim(claim_id: str, payload: dict, db: Session = Depends(get_db),
                 user: models.User = Depends(require_permission("warranty.claims.manage"))):
    claim = db.query(models.WarrantyClaim).filter(models.WarrantyClaim.id == claim_id).first()
    if not claim:
        raise HTTPException(404, "Claim not found.")
    status_str = payload.get("status", "")
    try:
        new_status = models.WarrantyClaimStatus(status_str)
    except ValueError:
        raise HTTPException(400, f"Invalid status: {status_str}")
    try:
        warranty_service.update_claim_status(db, claim, new_status, user, notes=payload.get("notes", ""))
    except ValueError as e:
        raise HTTPException(400, str(e))
    db.commit()
    return {"success": True}


@router.post("/warranty/scan-expiring")
def scan_expiring(db: Session = Depends(get_db), user: models.User = Depends(require_permission("warranty.manage"))):
    n = warranty_service.scan_expiring_warranties(db)
    db.commit()
    log_action(db, user, "WARRANTY_SCAN", entity_type="warranty", new_value=str(n))
    db.commit()
    return {"success": True, "notified": n}


# ── permission matrix ───────────────────────────────────────────────

@router.get("/permissions/matrix")
def get_permission_matrix(user: models.User = Depends(require_roles(models.RoleName.PRIMARY_ADMIN))):
    return {
        "permissions": ALL_PERMISSIONS,
        "matrix": permission_matrix(),
        "roles": ["CLIENT", "ADMIN", "SUPER_ADMIN", "PRIMARY_ADMIN"],
    }


# ── settings (system + website) ─────────────────────────────────────

@router.get("/settings")
def get_settings(db: Session = Depends(get_db), user: models.User = Depends(require_permission("system.settings"))):
    rows = db.query(models.SystemSetting).all()
    return {r.key: r.value for r in rows}


@router.put("/settings")
def update_settings(payload: dict, db: Session = Depends(get_db),
                    user: models.User = Depends(require_permission("system.settings"))):
    for k, v in payload.items():
        if not isinstance(k, str) or len(k) > 80:
            continue
        row = db.query(models.SystemSetting).filter(models.SystemSetting.key == k).first()
        if row:
            row.value = str(v)[:5000]
        else:
            db.add(models.SystemSetting(key=k, value=str(v)[:5000]))
    log_action(db, user, "SETTINGS_UPDATED", entity_type="settings", new_value=",".join(payload.keys()))
    db.commit()
    return {"success": True}


@router.get("/website-content")
def get_website_content(db: Session = Depends(get_db), user: models.User = Depends(require_permission("website.settings"))):
    rows = db.query(models.WebsiteContent).all()
    return {r.key: r.value for r in rows}


@router.put("/website-content")
def update_website_content(payload: dict, db: Session = Depends(get_db),
                           user: models.User = Depends(require_permission("website.settings"))):
    for k, v in payload.items():
        if not isinstance(k, str) or len(k) > 80:
            continue
        row = db.query(models.WebsiteContent).filter(models.WebsiteContent.key == k).first()
        if row:
            row.value = str(v)[:10000]
        else:
            db.add(models.WebsiteContent(key=k, value=str(v)[:10000]))
    log_action(db, user, "WEBSITE_CONTENT_UPDATED", entity_type="website", new_value=",".join(payload.keys()))
    db.commit()
    return {"success": True}


# ── FAQs ────────────────────────────────────────────────────────────

@router.get("/faqs")
def admin_list_faqs(db: Session = Depends(get_db), user: models.User = Depends(require_permission("faqs.manage"))):
    faqs = db.query(models.FAQ).order_by(models.FAQ.sort_order).all()
    return [{"id": f.id, "question": f.question, "answer": f.answer, "category": f.category,
             "sort_order": f.sort_order, "is_active": f.is_active} for f in faqs]


@router.post("/faqs")
def create_faq(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(require_permission("faqs.manage"))):
    faq = models.FAQ(
        question=payload.get("question", "").strip(),
        answer=payload.get("answer", "").strip(),
        category=payload.get("category", "GENERAL"),
        sort_order=int(payload.get("sort_order", 0)),
        is_active=bool(payload.get("is_active", True)),
    )
    if not faq.question or not faq.answer:
        raise HTTPException(400, "Question and answer required.")
    db.add(faq)
    db.commit()
    return {"success": True, "id": faq.id}


@router.put("/faqs/{faq_id}")
def update_faq(faq_id: str, payload: dict, db: Session = Depends(get_db),
               user: models.User = Depends(require_permission("faqs.manage"))):
    faq = db.query(models.FAQ).filter(models.FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(404, "FAQ not found.")
    for field in ("question", "answer", "category"):
        if field in payload:
            setattr(faq, field, str(payload[field]))
    if "sort_order" in payload:
        faq.sort_order = int(payload["sort_order"])
    if "is_active" in payload:
        faq.is_active = bool(payload["is_active"])
    db.commit()
    return {"success": True}


@router.delete("/faqs/{faq_id}")
def delete_faq(faq_id: str, db: Session = Depends(get_db), user: models.User = Depends(require_permission("faqs.manage"))):
    faq = db.query(models.FAQ).filter(models.FAQ.id == faq_id).first()
    if not faq:
        raise HTTPException(404, "FAQ not found.")
    faq.is_active = False
    db.commit()
    return {"success": True}


# ── contact enquiries ───────────────────────────────────────────────

@router.get("/enquiries")
def list_enquiries(db: Session = Depends(get_db), user: models.User = Depends(require_permission("enquiries.view"))):
    rows = db.query(models.ContactEnquiry).order_by(models.ContactEnquiry.created_at.desc()).limit(300).all()
    return [{"id": e.id, "name": e.name, "email": e.email, "phone": e.phone, "subject": e.subject,
             "message": e.message, "status": e.status.value if e.status else "",
             "created_at": e.created_at.isoformat() if e.created_at else ""} for e in rows]


@router.post("/enquiries/{enq_id}/status")
def update_enquiry(enq_id: str, payload: dict, db: Session = Depends(get_db),
                   user: models.User = Depends(require_permission("enquiries.manage"))):
    enq = db.query(models.ContactEnquiry).filter(models.ContactEnquiry.id == enq_id).first()
    if not enq:
        raise HTTPException(404, "Enquiry not found.")
    status_str = payload.get("status", "")
    try:
        enq.status = models.EnquiryStatus(status_str)
    except ValueError:
        raise HTTPException(400, "Invalid status.")
    if "internal_notes" in payload:
        enq.internal_notes = str(payload["internal_notes"])
    log_action(db, user, "ENQUIRY_UPDATED", entity_type="enquiry", entity_id=enq.id, new_value=status_str)
    db.commit()
    return {"success": True}


# ── project public flag ─────────────────────────────────────────────

@router.post("/projects/{project_id}/public")
def set_project_public(project_id: str, payload: dict, db: Session = Depends(get_db),
                       user: models.User = Depends(require_permission("projects.edit"))):
    p = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not p:
        raise HTTPException(404, "Project not found.")
    p.is_public = bool(payload.get("is_public", False))
    if "public_description" in payload:
        p.public_description = str(payload["public_description"])[:2000]
    log_action(db, user, "PROJECT_PUBLICITY", entity_type="project", entity_id=p.id,
               new_value=str(p.is_public))
    db.commit()
    return {"success": True, "is_public": p.is_public}


# ── announcements ───────────────────────────────────────────────────

@router.get("/announcements")
def list_announcements(db: Session = Depends(get_db), user: models.User = Depends(require_permission("website.settings"))):
    rows = db.query(models.Announcement).order_by(models.Announcement.created_at.desc()).all()
    return [{
        "id": a.id, "title": a.title, "message": a.message, "cta_text": a.cta_text,
        "cta_url": a.cta_url, "start_date": a.start_date, "end_date": a.end_date,
        "is_published": a.is_published,
        "created_at": a.created_at.isoformat() if a.created_at else "",
    } for a in rows]


@router.post("/announcements")
def create_announcement(payload: dict, db: Session = Depends(get_db),
                        user: models.User = Depends(require_permission("website.settings"))):
    a = models.Announcement(
        title=(payload.get("title") or "").strip(),
        message=(payload.get("message") or "").strip(),
        cta_text=payload.get("cta_text") or "",
        cta_url=payload.get("cta_url") or "",
        start_date=payload.get("start_date") or None,
        end_date=payload.get("end_date") or None,
        is_published=bool(payload.get("is_published", False)),
    )
    if not a.title or not a.message:
        raise HTTPException(400, "Title and message required.")
    db.add(a)
    log_action(db, user, "ANNOUNCEMENT_CREATED", entity_type="announcement", entity_id=a.id)
    db.commit()
    return {"success": True, "id": a.id}


@router.put("/announcements/{ann_id}")
def update_announcement(ann_id: str, payload: dict, db: Session = Depends(get_db),
                        user: models.User = Depends(require_permission("website.settings"))):
    a = db.query(models.Announcement).filter(models.Announcement.id == ann_id).first()
    if not a:
        raise HTTPException(404, "Announcement not found.")
    for field in ("title", "message", "cta_text", "cta_url", "start_date", "end_date"):
        if field in payload:
            setattr(a, field, payload[field])
    if "is_published" in payload:
        a.is_published = bool(payload["is_published"])
    log_action(db, user, "ANNOUNCEMENT_UPDATED", entity_type="announcement", entity_id=a.id)
    db.commit()
    return {"success": True}


# ── branding upload ─────────────────────────────────────────────────

ALLOWED_BRAND = {"image/png", "image/jpeg", "image/webp", "image/svg+xml", "image/x-icon", "image/vnd.microsoft.icon"}
MAX_BRAND_BYTES = 2 * 1024 * 1024


@router.post("/branding/upload")
async def upload_branding(kind: str = Form(...), file: UploadFile = File(...),
                          db: Session = Depends(get_db),
                          user: models.User = Depends(require_permission("website.settings"))):
    if kind not in ("logo", "favicon", "hero"):
        raise HTTPException(400, "kind must be logo, favicon, or hero.")
    ctype = (file.content_type or "").lower()
    if ctype not in ALLOWED_BRAND:
        raise HTTPException(400, "Only PNG, JPEG, WebP, SVG or ICO images are allowed.")
    raw = await file.read()
    if len(raw) > MAX_BRAND_BYTES:
        raise HTTPException(400, "File too large (max 2 MB).")
    import os, re
    from ..config import settings
    ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
               "image/svg+xml": ".svg", "image/x-icon": ".ico", "image/vnd.microsoft.icon": ".ico"}
    ext = ext_map.get(ctype, ".png")
    dest_dir = os.path.join(settings.upload_dir, "branding")
    os.makedirs(dest_dir, exist_ok=True)
    safe = re.sub(r"[^a-z0-9_-]", "", kind)
    path = os.path.join(dest_dir, f"{safe}{ext}")
    with open(path, "wb") as f:
        f.write(raw)
    public = f"/uploads/branding/{safe}{ext}"
    key = f"brand_{kind}_url"
    row = db.query(models.SystemSetting).filter(models.SystemSetting.key == key).first()
    if row:
        row.value = public
    else:
        db.add(models.SystemSetting(key=key, value=public))
    log_action(db, user, "BRANDING_UPLOAD", entity_type="settings", entity_id=key, new_value=public)
    db.commit()
    return {"success": True, "url": public, "key": key}
