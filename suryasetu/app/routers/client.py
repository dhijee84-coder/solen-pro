import os
import re
import shutil
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..dependencies import require_roles
from ..services import project_service, payment_service, notification_service
from ..services.audit_service import log_action

router = APIRouter(prefix="/api/client", tags=["client"])

client_only = require_roles(models.RoleName.CLIENT)

TARIFF = 7.10


def _profile(db: Session, user: models.User) -> models.ClientProfile:
    p = db.query(models.ClientProfile).filter(models.ClientProfile.user_id == user.id).first()
    if not p:
        raise HTTPException(404, "Client profile not found.")
    return p


@router.get("/me")
def my_overview(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    cp = p.client_project
    stages = db.query(models.ProjectStage).filter(models.ProjectStage.client_id == p.id).order_by(models.ProjectStage.stage_number).all()
    unread = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == user.id, models.Notification.is_read == False  # noqa: E712
    ).count()
    total_paid = sum(pay.amount for pay in p.payments if pay.status == models.PaymentStatus.SUCCESS)
    from ..services import warranty_service
    exp_days = warranty_service.get_expiring_days(db)
    panels = db.query(models.Panel).filter(models.Panel.client_id == p.id).all()
    w_counts = {"total": len(panels), "active": 0, "expiring_soon": 0, "expired": 0, "void": 0}
    for pan in panels:
        st = pan.computed_warranty_status(exp_days)
        if st == "ACTIVE":
            w_counts["active"] += 1
        elif st == "EXPIRING_SOON":
            w_counts["expiring_soon"] += 1
        elif st == "EXPIRED":
            w_counts["expired"] += 1
        else:
            w_counts["void"] += 1
    return {
        "user": {"id": user.id, "name": user.full_name, "phone": user.phone, "email": user.email},
        "profile": {
            "id": p.id, "kyc_status": p.kyc_status, "onboarding_stage": p.onboarding_stage,
            "pan_number": p.pan_number, "aadhaar_masked": p.aadhaar_masked,
            "visibility": {
                "show_generation": p.show_generation, "show_payments": p.show_payments,
                "show_project": p.show_project, "show_panels": p.show_panels,
                "show_documents": p.show_documents, "show_services": p.show_services,
                "show_support": p.show_support, "show_notifications": p.show_notifications,
            },
            "admin_notes": p.admin_notes,
        },
        "electricity": _electricity_dict(p.electricity_connection),
        "project": {
            "project_name": cp.project.project_name if cp else None,
            "project_code": cp.project.project_code if cp else None,
            "allocated_panels": cp.allocated_panel_count if cp else 0,
            "allocated_capacity_kw": cp.allocated_capacity_kw if cp else 0,
            "contract_total": cp.contract_total if cp else 0,
        } if cp else None,
        "stages": [_stage_dict(s) for s in stages],
        "payments_total_paid": total_paid,
        "unread_notifications": unread,
        "warranty": w_counts,
    }


def _electricity_dict(ec):
    if not ec:
        return None
    return {
        "rr_number": ec.rr_number, "discom": ec.discom, "division": ec.division,
        "service_address": ec.service_address, "tariff": ec.tariff,
        "sanctioned_load_kw": ec.sanctioned_load_kw, "avg_monthly_units": ec.avg_monthly_units,
        "avg_monthly_bill": ec.avg_monthly_bill, "phase": ec.phase,
        "proposed_kw": ec.proposed_kw, "system_cost": ec.system_cost,
        "subsidy_estimate": ec.subsidy_estimate, "payable_amount": ec.payable_amount,
    }


def _stage_dict(s: models.ProjectStage):
    return {
        "id": s.id, "stage_number": s.stage_number, "stage_name": s.stage_name,
        "percentage": s.percentage, "status": s.status.value,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "completed_at": s.completed_at.isoformat() if s.completed_at else None,
        "payment_status": s.payment_status, "notes": s.notes,
    }


# ── KYC ─────────────────────────────────────────────────────────────

@router.post("/kyc/pan")
def verify_pan(payload: schemas.PanVerifyIn, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    pan = payload.pan_number.upper().strip()
    if not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan):
        raise HTTPException(400, "PAN must be 5 letters, then 4 digits, then 1 letter.")
    p = _profile(db, user)
    p.pan_number = pan
    p.pan_name = user.full_name.upper()
    p.pan_verified_at = datetime.utcnow()
    log_action(db, user, "DOCUMENT_VERIFIED", entity_type="client", entity_id=p.id, new_value="PAN")
    db.commit()
    return {"success": True, "pan_number": pan, "verified_at": p.pan_verified_at.isoformat()}


@router.post("/kyc/aadhaar")
def verify_aadhaar(payload: schemas.AadhaarVerifyIn, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    num = re.sub(r"\D", "", payload.aadhaar_number)
    if len(num) != 12:
        raise HTTPException(400, "Aadhaar must be exactly 12 digits.")
    p = _profile(db, user)
    p.aadhaar_masked = "XXXX XXXX " + num[-4:]
    p.aadhaar_verified_at = datetime.utcnow()
    if p.pan_number:
        p.kyc_status = "VERIFIED"
        p.onboarding_stage = "KYC_DONE"
    log_action(db, user, "DOCUMENT_VERIFIED", entity_type="client", entity_id=p.id, new_value="AADHAAR")
    db.commit()
    return {"success": True, "aadhaar_masked": p.aadhaar_masked}


# ── electricity bill / plant sizing ──────────────────────────────────

@router.post("/bill/draft")
def bill_draft(payload: schemas.BillDraftIn, user: models.User = Depends(client_only)):
    """Mirrors the prototype's OCR-simulation step; the client reviews before saving."""
    units = payload.avg_monthly_units
    kw = max(1, min(10, round(units / 120)))
    cost = kw * 62000
    subsidy = min(78000, 78000 if kw >= 3 else kw * 30000)
    return {
        "rr_number": payload.rr_number, "discom": payload.discom, "division": payload.division,
        "service_address": payload.service_address, "tariff": payload.tariff,
        "sanctioned_load_kw": payload.sanctioned_load_kw or round(units / 190 * 2) / 2,
        "avg_monthly_units": units, "avg_monthly_bill": round(units * TARIFF),
        "phase": "Three phase" if units > 420 else "Single phase",
        "proposed_kw": kw, "system_cost": cost, "subsidy_estimate": subsidy, "payable_amount": cost - subsidy,
    }


@router.post("/bill/save")
def bill_save(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    ec = p.electricity_connection
    if not ec:
        ec = models.ElectricityConnection(client_id=p.id)
        db.add(ec)
    for f in ["rr_number", "discom", "division", "service_address", "tariff", "phase"]:
        if f in payload:
            setattr(ec, f, payload[f])
    ec.sanctioned_load_kw = float(payload.get("sanctioned_load_kw") or ec.sanctioned_load_kw or 0)
    ec.avg_monthly_units = float(payload.get("avg_monthly_units") or ec.avg_monthly_units or 0)
    ec.avg_monthly_bill = float(payload.get("avg_monthly_bill") or ec.avg_monthly_bill or 0)
    ec.proposed_kw = float(payload.get("proposed_kw") or ec.proposed_kw or 0)
    ec.system_cost = float(payload.get("system_cost") or ec.system_cost or 0)
    ec.subsidy_estimate = float(payload.get("subsidy_estimate") or ec.subsidy_estimate or 0)
    ec.payable_amount = float(payload.get("payable_amount") or ec.payable_amount or 0)
    p.onboarding_stage = "BILL_UPLOADED"
    log_action(db, user, "CLIENT_UPDATED", entity_type="client", entity_id=p.id, new_value="electricity bill saved")
    db.commit()
    return {"success": True}


@router.post("/documents/upload")
async def upload_document(
    document_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: models.User = Depends(client_only),
):
    p = _profile(db, user)
    if document_type not in models.DocumentType.__members__:
        raise HTTPException(400, "Unknown document type.")
    from ..services.storage import validate_document_upload, store_bytes, sanitize_filename
    data = await file.read()
    validate_document_upload(file, data)
    dest, stored_name, size = store_bytes(
        os.path.join("clients", p.id, document_type.lower()),
        file.filename or "upload.bin",
        data,
    )

    doc = models.Document(
        client_id=p.id, document_type=models.DocumentType[document_type],
        original_filename=sanitize_filename(file.filename or stored_name), stored_filename=stored_name, file_path=dest,
        mime_type=file.content_type or "", file_size=size, uploaded_by=user.id,
        status=models.DocumentStatus.UPLOADED,
    )
    db.add(doc)
    if document_type == "ELECTRICITY_BILL" and p.electricity_connection:
        p.electricity_connection.bill_file_path = dest
    log_action(db, user, "DOCUMENT_UPLOADED", entity_type="client", entity_id=p.id, new_value=document_type)
    db.commit()
    return {"success": True, "document_id": doc.id, "filename": file.filename}


@router.get("/documents")
def list_my_documents(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    docs = db.query(models.Document).filter(models.Document.client_id == p.id).order_by(models.Document.uploaded_at.desc()).all()
    return [{
        "id": d.id, "type": d.document_type.value, "filename": d.original_filename,
        "status": d.status.value, "uploaded_at": d.uploaded_at.isoformat(),
    } for d in docs]


@router.get("/documents/{document_id}/file")
def download_my_document(document_id: str, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    doc = db.query(models.Document).filter(
        models.Document.id == document_id, models.Document.client_id == p.id
    ).first()
    if not doc:
        raise HTTPException(404, "Document not found.")
    from ..services.storage import assert_under_upload_dir
    path = assert_under_upload_dir(doc.file_path)
    if not os.path.isfile(path):
        raise HTTPException(404, "File is no longer available.")
    return FileResponse(path, filename=doc.original_filename or doc.stored_filename, media_type=doc.mime_type or "application/octet-stream")


# ── payments ────────────────────────────────────────────────────────

@router.post("/payments/pay")
def make_payment(payload: schemas.PaymentIn, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    payment = payment_service.record_payment(db, p, payload.amount, payload.method, user, stage_id=payload.stage_id)
    return {
        "success": True, "payment_id": payment.id, "transaction_reference": payment.transaction_reference,
        "amount": payment.amount, "status": payment.status.value,
    }


@router.get("/payments")
def list_my_payments(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    pays = db.query(models.Payment).filter(models.Payment.client_id == p.id).order_by(models.Payment.created_at.desc()).all()
    return [{
        "id": x.id, "amount": x.amount, "method": x.payment_method, "status": x.status.value,
        "txn": x.transaction_reference, "created_at": x.created_at.isoformat(),
        "paid_at": x.paid_at.isoformat() if x.paid_at else None,
    } for x in pays]


# ── generation ──────────────────────────────────────────────────────

@router.get("/generation")
def my_generation(range: str = "day", db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    records = db.query(models.GenerationRecord).filter(models.GenerationRecord.client_id == p.id).order_by(models.GenerationRecord.date).all()
    total = sum(r.generation_kwh for r in records)
    co2 = sum(r.co2_saved_kg for r in records)
    return {
        "records": [{"date": r.date, "kwh": r.generation_kwh, "peak_kw": r.peak_kw, "co2_kg": r.co2_saved_kg} for r in records],
        "lifetime_kwh": round(total, 1),
        "lifetime_co2_kg": round(co2, 1),
        "this_month_kwh": round(sum(r.generation_kwh for r in records if r.date[:7] == datetime.utcnow().strftime("%Y-%m")), 1),
        "today_kwh": round(sum(r.generation_kwh for r in records if r.date == datetime.utcnow().strftime("%Y-%m-%d")), 1),
        "this_week_kwh": round(sum(r.generation_kwh for r in records if r.date >= (datetime.utcnow() - timedelta(days=6)).strftime("%Y-%m-%d")), 1),
    }


# ── services / tickets / notifications ───────────────────────────────

@router.get("/services/catalog")
def services_catalog(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    services = db.query(models.Service).filter(models.Service.is_active == True).all()  # noqa: E712
    return [{"id": s.id, "name": s.name, "description": s.description, "base_price": s.base_price} for s in services]


@router.post("/services/request")
def request_service(payload: schemas.ServiceRequestIn, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    svc = db.query(models.Service).filter(models.Service.id == payload.service_id).first()
    if not svc:
        raise HTTPException(404, "Service not found.")
    sr = models.ClientServiceRequest(client_id=p.id, service_id=svc.id, notes=payload.notes)
    db.add(sr)
    db.flush()
    notification_service.notify_service_request(db, sr)
    log_action(db, user, "SERVICE_REQUESTED", entity_type="client", entity_id=p.id, new_value=svc.name)
    db.commit()
    return {"success": True, "request_id": sr.id}


@router.get("/services/my-requests")
def my_service_requests(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    reqs = db.query(models.ClientServiceRequest).filter(models.ClientServiceRequest.client_id == p.id).order_by(models.ClientServiceRequest.created_at.desc()).all()
    return [{
        "id": r.id, "service": r.service.name, "status": r.status.value,
        "quoted_price": r.quoted_price, "notes": r.notes, "created_at": r.created_at.isoformat(),
    } for r in reqs]


@router.post("/tickets")
def create_ticket(payload: schemas.TicketCreateIn, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    t = models.SupportTicket(client_id=p.id, subject=payload.subject, category=payload.category,
                              description=payload.description, priority=payload.priority)
    db.add(t)
    db.flush()
    notification_service.notify_client_question(db, t)
    db.commit()
    return {"success": True, "ticket_id": t.id}


@router.get("/tickets")
def my_tickets(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    ts = db.query(models.SupportTicket).filter(models.SupportTicket.client_id == p.id).order_by(models.SupportTicket.created_at.desc()).all()
    return [{"id": t.id, "subject": t.subject, "status": t.status.value, "priority": t.priority,
             "category": t.category, "description": t.description,
             "created_at": t.created_at.isoformat()} for t in ts]


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    t = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id, models.SupportTicket.client_id == p.id).first()
    if not t:
        raise HTTPException(404, "Ticket not found.")
    msgs = db.query(models.TicketMessage).filter(models.TicketMessage.ticket_id == t.id).order_by(models.TicketMessage.created_at).all()
    return {
        "id": t.id, "subject": t.subject, "status": t.status.value, "priority": t.priority,
        "category": t.category, "description": t.description,
        "created_at": t.created_at.isoformat(),
        "messages": [{
            "id": m.id, "sender_user_id": m.sender_user_id, "message": m.message,
            "created_at": m.created_at.isoformat(),
            "mine": m.sender_user_id == user.id,
        } for m in msgs],
    }


@router.post("/tickets/{ticket_id}/messages")
def ticket_reply(ticket_id: str, payload: schemas.TicketMessageIn, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    t = db.query(models.SupportTicket).filter(models.SupportTicket.id == ticket_id, models.SupportTicket.client_id == p.id).first()
    if not t:
        raise HTTPException(404, "Ticket not found.")
    if t.status in (models.TicketStatus.CLOSED, models.TicketStatus.RESOLVED):
        t.status = models.TicketStatus.WAITING_FOR_CLIENT
    msg = (payload.message or "").strip()
    if not msg:
        raise HTTPException(400, "Message required.")
    m = models.TicketMessage(ticket_id=t.id, sender_user_id=user.id, message=msg)
    db.add(m)
    db.commit()
    return {"success": True}


@router.get("/notifications")
def my_notifications(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    ns = db.query(models.Notification).filter(models.Notification.recipient_user_id == user.id).order_by(models.Notification.created_at.desc()).limit(50).all()
    return [{"id": n.id, "title": n.title, "message": n.message, "is_read": n.is_read,
             "type": n.type, "created_at": n.created_at.isoformat()} for n in ns]


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    ns = db.query(models.Notification).filter(
        models.Notification.recipient_user_id == user.id,
        models.Notification.is_read == False,  # noqa: E712
    ).all()
    for n in ns:
        n.is_read = True
    db.commit()
    return {"success": True, "updated": len(ns)}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: str, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    n = db.query(models.Notification).filter(models.Notification.id == notification_id, models.Notification.recipient_user_id == user.id).first()
    if not n:
        raise HTTPException(404, "Notification not found.")
    n.is_read = True
    db.commit()
    return {"success": True}


# ── panels + warranty ───────────────────────────────────────────────

from ..services import warranty_service


@router.get("/panels")
def my_panels(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    exp_days = warranty_service.get_expiring_days(db)
    panels = db.query(models.Panel).filter(models.Panel.client_id == p.id).all()
    return [{
        "id": pan.id,
        "serial_number": pan.serial_number,
        "manufacturer": pan.manufacturer,
        "model": pan.model,
        "watt_rating": pan.watt_rating,
        "status": pan.status.value if pan.status else "",
        "installation_date": pan.installation_date,
        "warranty_start": pan.warranty_start_date,
        "warranty_end": pan.warranty_end_date,
        "warranty_status": pan.computed_warranty_status(exp_days),
        "warranty_years": pan.warranty_years,
        "warranty_type": pan.warranty_type,
        "warranty_provider": pan.warranty_provider,
        "warranty_terms": pan.warranty_terms or "",
        "project_id": pan.project_id,
        "project_name": pan.project.project_name if pan.project else "",
    } for pan in panels]


@router.post("/warranty/claims")
def submit_warranty_claim(payload: dict, db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    panel_id = payload.get("panel_id")
    panel = db.query(models.Panel).filter(models.Panel.id == panel_id, models.Panel.client_id == p.id).first()
    if not panel:
        raise HTTPException(404, "Panel not found or not yours.")
    issue = (payload.get("issue_summary") or "").strip()
    if len(issue) < 5:
        raise HTTPException(400, "Please describe the issue.")
    claim = warranty_service.create_claim(
        db, panel, p,
        issue_summary=issue,
        description=payload.get("description", ""),
        date_discovered=payload.get("date_discovered"),
        contact_phone=payload.get("contact_phone", user.phone or ""),
        contact_email=payload.get("contact_email", user.email or ""),
    )
    db.commit()
    return {"success": True, "claim_id": claim.id}


@router.get("/warranty/claims")
def my_warranty_claims(db: Session = Depends(get_db), user: models.User = Depends(client_only)):
    p = _profile(db, user)
    claims = db.query(models.WarrantyClaim).filter(models.WarrantyClaim.client_id == p.id).order_by(
        models.WarrantyClaim.created_at.desc()).all()
    return [{
        "id": c.id, "panel_id": c.panel_id,
        "panel_serial": c.panel.serial_number if c.panel else "",
        "issue": c.issue_summary,
        "description": c.description, "status": c.status.value if c.status else "",
        "date_discovered": c.date_discovered,
        "created_at": c.created_at.isoformat() if c.created_at else "",
        "updated_at": c.updated_at.isoformat() if c.updated_at else "",
        "resolution_notes": c.resolution_notes or "",
    } for c in claims]
