from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.database import SessionLocal
from app.services import allocation_service, warranty_service
from tests.conftest import make_staff, make_project_with_panels, make_client_user, login_staff, register_client


def _allocate_with_warranty(db, days_until_end=400, serial_suffix="W"):
    phones = {"A": "9845210001", "B": "9845210002", "C": "9845210003", "D": "9845210004"}
    project = make_project_with_panels(db, f"WRN-{serial_suffix}", 2)
    user, profile = make_client_user(db, phones.get(serial_suffix, "9845210999"), "Warranty Client")
    admin = make_staff(db, models.RoleName.ADMIN, f"wadmin-{serial_suffix}")
    panels = allocation_service.allocate_panels(db, project.id, profile.id, 2, admin)
    start = datetime.utcnow().date() - timedelta(days=365)
    end = datetime.utcnow().date() + timedelta(days=days_until_end)
    for p in panels:
        p.warranty_start_date = start.isoformat()
        p.warranty_end_date = end.isoformat()
        p.warranty_years = 25
        p.warranty_provider = "Waaree"
    db.commit()
    return user, profile, panels, admin


def test_client_sees_own_panels_and_warranty_status(client):
    db = SessionLocal()
    user, profile, panels, admin = _allocate_with_warranty(db, days_until_end=400, serial_suffix="A")
    phone = user.phone
    db.close()
    register_client(client, phone, user.full_name)
    r = client.get("/api/client/panels")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all(p["warranty_status"] == "ACTIVE" for p in data)
    me = client.get("/api/client/me").json()
    assert me["warranty"]["total"] == 2
    assert me["warranty"]["active"] == 2


def test_client_creates_warranty_claim_and_staff_sees_it():
    db = SessionLocal()
    user, profile, panels, admin = _allocate_with_warranty(db, days_until_end=400, serial_suffix="B")
    phone = user.phone
    panel_id = panels[0].id
    db.close()

    client_api = TestClient(app)
    register_client(client_api, phone, user.full_name)
    r = client_api.post("/api/client/warranty/claims", json={
        "panel_id": panel_id,
        "issue_summary": "Microcrack on cell 12",
        "description": "Visible crack after hail.",
    })
    assert r.status_code == 200
    claim_id = r.json()["claim_id"]
    mine = client_api.get("/api/client/warranty/claims").json()
    assert any(c["id"] == claim_id for c in mine)
    assert mine[0]["status"] == "SUBMITTED"

    staff = TestClient(app)
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "claimadmin")
    db.close()
    login_staff(staff, "claimadmin")
    listed = staff.get("/api/admin/warranty/claims").json()
    assert any(c["id"] == claim_id for c in listed)


def test_valid_and_invalid_claim_transitions_and_client_sees_update():
    db = SessionLocal()
    user, profile, panels, admin = _allocate_with_warranty(db, days_until_end=400, serial_suffix="C")
    phone = user.phone
    panel_id = panels[0].id
    db.close()

    client_api = TestClient(app)
    register_client(client_api, phone, user.full_name)
    claim_id = client_api.post("/api/client/warranty/claims", json={
        "panel_id": panel_id, "issue_summary": "Hotspot on junction box",
    }).json()["claim_id"]

    staff = TestClient(app)
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "transadmin")
    db.close()
    login_staff(staff, "transadmin")

    bad = staff.post(f"/api/admin/warranty/claims/{claim_id}/status", json={"status": "REPLACED"})
    assert bad.status_code == 400

    ok = staff.post(f"/api/admin/warranty/claims/{claim_id}/status", json={
        "status": "UNDER_REVIEW", "notes": "Inspecting",
    })
    assert ok.status_code == 200

    updated = client_api.get("/api/client/warranty/claims").json()
    assert updated[0]["status"] == "UNDER_REVIEW"

    db = SessionLocal()
    logs = db.query(models.AuditLog).filter(models.AuditLog.action == "WARRANTY_CLAIM_UPDATED").all()
    assert logs
    db.close()


def test_scan_expiring_does_not_duplicate_notifications():
    db = SessionLocal()
    user, profile, panels, admin = _allocate_with_warranty(db, days_until_end=10, serial_suffix="D")
    n1 = warranty_service.scan_expiring_warranties(db)
    db.commit()
    n2 = warranty_service.scan_expiring_warranties(db)
    db.commit()
    assert n1 >= 1
    assert n2 == 0
    db.close()
