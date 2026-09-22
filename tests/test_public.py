from app import models
from app.database import SessionLocal
from tests.conftest import make_project_with_panels, make_staff


def test_public_routes_return_successfully(client):
    for path in ["/", "/about", "/solar", "/how-it-works", "/services", "/projects", "/faq", "/contact", "/login", "/staff-login"]:
        r = client.get(path)
        assert r.status_code == 200, path


def test_public_projects_respect_is_public(client):
    db = SessionLocal()
    make_project_with_panels(db, "PUB-1", 2, is_public=True, project_name="Public Park", public_description="Shown")
    make_project_with_panels(db, "HID-1", 2, is_public=False, project_name="Private Farm")
    db.close()
    r = client.get("/api/public/projects")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert "Public Park" in names
    assert "Private Farm" not in names


def test_faqs_and_services_load(client):
    db = SessionLocal()
    db.add(models.FAQ(question="What is SuryaSetu?", answer="A solar platform.", is_active=True))
    db.add(models.FAQ(question="Hidden?", answer="nope", is_active=False))
    db.add(models.Service(name="Cleaning", description="Panel wash", base_price=1500, is_active=True))
    db.add(models.Service(name="Secret", description="x", base_price=9, is_active=False))
    db.commit()
    db.close()
    faqs = client.get("/api/public/faqs").json()
    assert any(f["question"] == "What is SuryaSetu?" for f in faqs)
    assert not any(f["question"] == "Hidden?" for f in faqs)
    services = client.get("/api/public/services").json()
    assert any(s["name"] == "Cleaning" for s in services)
    assert not any(s["name"] == "Secret" for s in services)
    for s in services:
        assert "base_price" not in s and "price" not in s


def test_contact_form_creates_enquiry_and_notification(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "enqadmin")
    db.close()
    r = client.post("/api/public/contact", json={
        "name": "Visitor One",
        "email": "visitor@example.com",
        "phone": "9800000000",
        "subject": "Site visit",
        "message": "I would like a site survey next week please.",
    })
    assert r.status_code == 200
    db = SessionLocal()
    enq = db.query(models.ContactEnquiry).filter(models.ContactEnquiry.email == "visitor@example.com").first()
    assert enq is not None
    notes = db.query(models.Notification).filter(models.Notification.type == "ENQUIRY").all()
    assert notes
    db.close()


def test_contact_rejects_short_message(client):
    r = client.post("/api/public/contact", json={
        "name": "X", "email": "a@b.co", "message": "hi",
    })
    assert r.status_code in (400, 422)
