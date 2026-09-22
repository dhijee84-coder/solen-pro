from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.database import SessionLocal
from app.permissions import role_has_permission
from tests.conftest import make_staff, login_staff, register_client


def test_client_cannot_access_staff_apis(client):
    register_client(client, "9845000003")
    assert client.get("/api/admin/dashboard").status_code == 403
    assert client.get("/api/admin/clients").status_code == 403
    assert client.get("/api/admin/export/clients").status_code == 403
    assert client.get("/api/admin/permissions/matrix").status_code == 403
    assert client.get("/api/primary-admin/dashboard").status_code == 403
    assert client.get("/api/admin/warranty/claims").status_code == 403


def test_client_cannot_access_another_clients_data():
    a = TestClient(app)
    b = TestClient(app)
    register_client(a, "9845111001", "Alice")
    register_client(b, "9845111002", "Bob")
    alice = a.get("/api/client/me").json()
    bob = b.get("/api/client/me").json()
    assert alice["profile"]["id"] != bob["profile"]["id"]

    t = a.post("/api/client/tickets", json={
        "subject": "Alice only", "category": "GENERAL", "description": "Private ticket body here", "priority": "NORMAL",
    })
    assert t.status_code == 200
    ticket_id = t.json()["ticket_id"]
    assert b.get(f"/api/client/tickets/{ticket_id}").status_code == 404
    assert b.post(f"/api/client/tickets/{ticket_id}/messages", json={"message": "snooping"}).status_code == 404

    pays_a = a.get("/api/client/payments").json()
    pays_b = b.get("/api/client/payments").json()
    assert isinstance(pays_a, list) and isinstance(pays_b, list)
    a_ids = {p["id"] for p in pays_a}
    b_ids = {p["id"] for p in pays_b}
    assert a_ids.isdisjoint(b_ids)


def test_admin_cannot_export_restricted_csv(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "regularadmin")
    db.close()
    login_staff(client, "regularadmin")
    assert client.get("/api/admin/export/clients").status_code == 403
    assert client.get("/api/admin/export/payments").status_code == 403
    assert client.get("/api/admin/reports/summary").status_code == 200  # reports.view is allowed


def test_admin_cannot_access_permission_matrix(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "regularadmin")
    db.close()
    login_staff(client, "regularadmin")
    assert client.get("/api/admin/permissions/matrix").status_code == 403
    assert client.get("/api/admin/settings").status_code == 403
    assert client.get("/api/primary-admin/dashboard").status_code == 403


def test_admin_cannot_manage_super_admin(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "regularadmin")
    db.close()
    login_staff(client, "regularadmin")
    r = client.post("/api/admin/staff", json={
        "full_name": "X", "username": "newsuper", "password": "pw123456", "role": "SUPER_ADMIN",
    })
    assert r.status_code == 403
    r2 = client.post("/api/admin/staff", json={
        "full_name": "Y", "username": "newadmin", "password": "pw123456", "role": "ADMIN",
    })
    assert r2.status_code == 403  # Admin cannot create staff at all


def test_super_admin_cannot_manage_primary_admin(client):
    db = SessionLocal()
    primary = make_staff(db, models.RoleName.PRIMARY_ADMIN, "theprimary")
    primary_id = primary.id
    make_staff(db, models.RoleName.SUPER_ADMIN, "thesuper")
    db.close()
    login_staff(client, "thesuper")
    assert client.get("/api/primary-admin/dashboard").status_code == 403
    assert client.get("/api/admin/permissions/matrix").status_code == 403
    r = client.put(f"/api/admin/staff/{primary_id}", json={"is_active": False})
    assert r.status_code in (403, 404)
    r2 = client.post("/api/admin/staff", json={
        "full_name": "Another Super", "username": "super2", "password": "pw123456", "role": "SUPER_ADMIN",
    })
    assert r2.status_code == 403
    # Super Admin CAN create an Admin
    r3 = client.post("/api/admin/staff", json={
        "full_name": "Ops", "username": "opsadmin", "password": "pw123456", "role": "ADMIN",
    })
    assert r3.status_code == 200


def test_primary_admin_can_access_administration(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.PRIMARY_ADMIN, "owner")
    db.close()
    login_staff(client, "owner")
    assert client.get("/api/primary-admin/dashboard").status_code == 200
    assert client.get("/api/admin/permissions/matrix").status_code == 200
    assert client.get("/api/admin/settings").status_code == 200
    assert client.get("/api/admin/export/clients").status_code == 200
    assert client.get("/api/admin/staff").status_code == 200
    r = client.post("/api/admin/staff", json={
        "full_name": "New Super", "username": "newsuper", "password": "pw123456", "role": "SUPER_ADMIN",
    })
    assert r.status_code == 200


def test_permission_matrix_matches_code():
    assert role_has_permission(models.RoleName.PRIMARY_ADMIN, "system.settings")
    assert not role_has_permission(models.RoleName.ADMIN, "reports.export")
    assert not role_has_permission(models.RoleName.ADMIN, "roles.manage")
    assert not role_has_permission(models.RoleName.SUPER_ADMIN, "system.settings")
    assert role_has_permission(models.RoleName.SUPER_ADMIN, "reports.export")
    assert not role_has_permission(models.RoleName.CLIENT, "clients.view")
