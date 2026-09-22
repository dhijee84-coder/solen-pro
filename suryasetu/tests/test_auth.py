from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.database import SessionLocal
from tests.conftest import make_staff, login_staff, register_client


def test_client_otp_registration_and_login(client):
    r = client.post("/api/auth/otp/send", json={"phone": "9845000001"})
    assert r.status_code == 200
    code = r.json()["dev_otp"]
    r2 = client.post("/api/auth/otp/verify", json={"phone": "9845000001", "code": code, "full_name": "Test User"})
    assert r2.status_code == 200
    assert r2.json()["is_new_client"] is True
    r3 = client.get("/api/client/me")
    assert r3.status_code == 200
    assert r3.json()["user"]["name"] == "Test User"


def test_invalid_otp_rejected(client):
    client.post("/api/auth/otp/send", json={"phone": "9845000002"})
    r = client.post("/api/auth/otp/verify", json={"phone": "9845000002", "code": "0000"})
    assert r.status_code == 400


def test_invalid_phone_rejected(client):
    r = client.post("/api/auth/otp/send", json={"phone": "123"})
    assert r.status_code == 400


def test_admin_login_success(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "testadmin")
    db.close()
    r = client.post("/api/auth/admin/login", json={"username": "testadmin", "password": "pw123456"})
    assert r.status_code == 200
    assert r.json()["user"]["role"] == "ADMIN"
    cookie = r.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie or "httponly" in cookie.lower()
    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["role"] == "ADMIN"


def test_super_admin_login(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.SUPER_ADMIN, "testsuper")
    db.close()
    login_staff(client, "testsuper")
    assert client.get("/api/auth/me").json()["role"] == "SUPER_ADMIN"


def test_primary_admin_login(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.PRIMARY_ADMIN, "testprimary")
    db.close()
    login_staff(client, "testprimary")
    assert client.get("/api/auth/me").json()["role"] == "PRIMARY_ADMIN"


def test_invalid_admin_credentials(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "realadmin")
    db.close()
    r = client.post("/api/auth/admin/login", json={"username": "realadmin", "password": "wrong"})
    assert r.status_code == 401
    r2 = client.post("/api/auth/admin/login", json={"username": "nobody", "password": "pw123456"})
    assert r2.status_code == 401
    assert "password" not in r2.text.lower() or "invalid" in r2.json()["detail"].lower()


def test_logout_clears_session(client):
    register_client(client, "9845000099")
    assert client.get("/api/client/me").status_code == 200
    r = client.post("/api/auth/logout")
    assert r.status_code == 200
    assert client.get("/api/client/me").status_code == 401
    assert client.get("/api/admin/dashboard").status_code == 401


def test_unauthorized_access_without_cookie(client):
    assert client.get("/api/client/me").status_code == 401
    assert client.get("/api/admin/dashboard").status_code == 401
    assert client.get("/api/admin/clients").status_code == 401
    assert client.get("/api/primary-admin/dashboard").status_code == 401


def test_client_cannot_use_staff_login(client):
    register_client(client, "9845000088", "Only Client")
    # Client accounts have no username/password
    r = client.post("/api/auth/admin/login", json={"username": "Only Client", "password": "x"})
    assert r.status_code == 401
