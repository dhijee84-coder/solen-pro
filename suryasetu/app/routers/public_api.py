"""Public (unauthenticated) API for website content, contact form, FAQs, public projects."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from ..database import get_db
from .. import models
from ..services.audit_service import log_action
from ..rate_limit import limiter
from ..config import settings

router = APIRouter(prefix="/api/public", tags=["public"])


class ContactIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    email: str = Field(..., min_length=5, max_length=150)
    phone: str = Field(default="", max_length=20)
    subject: str = Field(default="", max_length=200)
    message: str = Field(..., min_length=10, max_length=5000)


@router.get("/content")
def website_content(db: Session = Depends(get_db)):
    rows = db.query(models.WebsiteContent).all()
    return {r.key: r.value for r in rows}


@router.get("/settings")
def public_settings(db: Session = Depends(get_db)):
    keys = [
        "company_name", "company_phone", "company_email", "company_address",
        "support_email", "support_phone", "hero_heading", "hero_description",
        "hero_cta", "about_mission", "about_vision", "about_body",
        "footer_text", "social_linkedin", "social_instagram", "social_facebook",
        "social_youtube", "social_x", "seo_title", "seo_description",
        "primary_color", "accent_color",
        "section_projects", "section_services", "section_faq", "section_contact",
        "brand_logo_url", "brand_favicon_url", "brand_hero_url",
    ]
    out = {}
    for k in keys:
        row = db.query(models.SystemSetting).filter(models.SystemSetting.key == k).first()
        if row:
            out[k] = row.value
        else:
            wc = db.query(models.WebsiteContent).filter(models.WebsiteContent.key == k).first()
            out[k] = wc.value if wc else ""
    # defaults
    out.setdefault("company_name", "Solan")
    out.setdefault("hero_heading", "You buy the panels. We run the farm.")
    out.setdefault("hero_description", "Solan builds solar parks on open land. Clients purchase panels. We install, maintain and operate everything — and you pay for the energy those panels generate.")
    out.setdefault("hero_cta", "Get Started")
    out.setdefault("section_projects", "on")
    out.setdefault("section_services", "on")
    out.setdefault("section_faq", "on")
    out.setdefault("section_contact", "on")
    return out


@router.get("/projects")
def public_projects(db: Session = Depends(get_db)):
    projects = db.query(models.Project).filter(models.Project.is_public == True).all()
    return [{
        "id": p.id,
        "name": p.project_name,
        "code": p.project_code,
        "location": p.location,
        "capacity_kw": p.capacity_kw,
        "total_panels": p.total_panels,
        "status": p.status.value if p.status else "",
        "description": p.public_description or "",
    } for p in projects]


@router.get("/services")
def public_services(db: Session = Depends(get_db)):
    services = db.query(models.Service).filter(models.Service.is_active == True).all()
    return [{
        "id": s.id,
        "name": s.name,
        "description": s.description,
        # price intentionally omitted unless configured as public later
    } for s in services]


@router.get("/faqs")
def public_faqs(db: Session = Depends(get_db)):
    faqs = (
        db.query(models.FAQ)
        .filter(models.FAQ.is_active == True)
        .order_by(models.FAQ.sort_order, models.FAQ.created_at)
        .all()
    )
    return [{
        "id": f.id,
        "question": f.question,
        "answer": f.answer,
        "category": f.category,
    } for f in faqs]


@router.get("/announcements")
def public_announcements(db: Session = Depends(get_db)):
    from datetime import datetime
    today = datetime.utcnow().strftime("%Y-%m-%d")
    rows = db.query(models.Announcement).filter(models.Announcement.is_published == True).all()
    out = []
    for a in rows:
        if a.start_date and a.start_date > today:
            continue
        if a.end_date and a.end_date < today:
            continue
        out.append({
            "id": a.id,
            "title": a.title,
            "message": a.message,
            "cta_text": a.cta_text,
            "cta_url": a.cta_url,
        })
    return out


@router.post("/contact", dependencies=[Depends(limiter("contact", settings.rate_limit_contact))])
def submit_contact(payload: ContactIn, db: Session = Depends(get_db)):
    # basic anti-spam: reject if message looks like pure spam
    if len(payload.message.strip()) < 10:
        raise HTTPException(400, "Message is too short.")
    enq = models.ContactEnquiry(
        name=payload.name.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone.strip(),
        subject=payload.subject.strip() or "Website enquiry",
        message=payload.message.strip(),
        status=models.EnquiryStatus.NEW,
    )
    db.add(enq)
    db.flush()
    log_action(db, None, "CONTACT_ENQUIRY", entity_type="enquiry", entity_id=enq.id, new_value=payload.email)
    # Notify staff in-app
    staff = db.query(models.User).filter(
        models.User.role.in_([models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN, models.RoleName.PRIMARY_ADMIN]),
        models.User.is_active == True,
    ).limit(20).all()
    for u in staff:
        db.add(models.Notification(
            recipient_user_id=u.id,
            type="ENQUIRY",
            title="New website enquiry",
            message=f"From {payload.name}: {payload.subject or 'General enquiry'}",
            priority="NORMAL",
            related_entity="enquiry",
            related_entity_id=enq.id,
        ))
    db.commit()
    return {"success": True, "message": "Thank you. We have received your message and will respond shortly.", "id": enq.id}
