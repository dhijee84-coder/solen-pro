"""Shared pytest fixtures. Environment is forced to `test` before the app imports."""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(ROOT, "test_suryasetu.db")
os.environ["SECRET_KEY"] = "test-secret-key-for-suryasetu-unit-tests-32b"
os.environ["DEV_OTP"] = "1234"
os.environ["RATE_LIMIT_ENABLED"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app import models
from app.security import hash_password
from app.services import allocation_service  # noqa: F401


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def make_staff(db, role, username, password="pw123456"):
    u = models.User(
        role=role,
        full_name=username,
        username=username,
        hashed_password=hash_password(password),
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def make_project_with_panels(db, code="TST-001", count=4, **kwargs):
    p = models.Project(
        project_code=code,
        project_name=kwargs.get("project_name", "Test Project"),
        status=models.ProjectStatus.ACTIVE,
        total_panels=count,
        is_public=kwargs.get("is_public", False),
        public_description=kwargs.get("public_description", ""),
        location=kwargs.get("location", "Test City"),
        capacity_kw=count * 0.4,
    )
    db.add(p)
    db.flush()
    for i in range(count):
        db.add(models.Panel(
            serial_number=f"{code}-P{i+1:03d}",
            project_id=p.id,
            added_sequence=i + 1,
            status=models.PanelStatus.AVAILABLE,
            watt_rating=400,
            manufacturer="Waaree",
            model="WSM-400",
            warranty_years=25,
        ))
    db.commit()
    db.refresh(p)
    return p


def make_client_user(db, phone, name="Test Client"):
    u = models.User(role=models.RoleName.CLIENT, full_name=name, phone=phone)
    db.add(u)
    db.flush()
    profile = models.ClientProfile(user_id=u.id, kyc_status="VERIFIED", onboarding_stage="ACTIVE")
    db.add(profile)
    db.commit()
    db.refresh(u)
    db.refresh(profile)
    return u, profile


def login_staff(client: TestClient, username, password="pw123456"):
    r = client.post("/api/auth/admin/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r


def register_client(client: TestClient, phone, name="Test User"):
    client.post("/api/auth/otp/send", json={"phone": phone})
    r = client.post("/api/auth/otp/verify", json={"phone": phone, "code": "1234", "full_name": name})
    assert r.status_code == 200, r.text
    return r
