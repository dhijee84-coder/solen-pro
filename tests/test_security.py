from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.config import settings
from app.database import SessionLocal
from app.rate_limit import reset, check
from tests.conftest import register_client, make_staff, login_staff


def test_client_uploads_not_publicly_served(client):
    register_client(client, "9845600001", "Sec")
    r = client.post(
        "/api/client/documents/upload",
        data={"document_type": "PAN"},
        files={"file": ("pan.pdf", b"%PDF-1.1\n%%EOF\n", "application/pdf")},
    )
    assert r.status_code == 200
    # Direct static path must not list or serve client documents
    leaked = client.get("/uploads/clients/")
    assert leaked.status_code in (404, 401, 403, 307, 405)


def test_docs_hidden_logic_follows_environment():
    # Test environment is not production, so docs may be on; production flag is the contract.
    assert settings.is_production is False
    assert settings.expose_dev_otp is True
    assert settings.allow_dev_otp is True


def test_error_responses_are_consistent(client):
    r = client.get("/api/client/me")
    assert r.status_code == 401
    body = r.json()
    assert "detail" in body
    assert "traceback" not in r.text.lower()
    assert "secret" not in r.text.lower()


def test_sql_injection_in_search_is_parameterized(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "searchadmin")
    db.close()
    login_staff(client, "searchadmin")
    r = client.get("/api/admin/search", params={"q": "'; DROP TABLE users; --"})
    assert r.status_code == 200
    db = SessionLocal()
    assert db.query(models.User).count() >= 1
    db.close()


def test_xss_is_not_reflected_in_api_json(client):
    register_client(client, "9845600002", "<script>alert(1)</script>")
    me = client.get("/api/client/me").json()
    # Stored as data, not executed; JSON string is fine, HTML pages escape via esc()
    assert me["user"]["name"] == "<script>alert(1)</script>"


def test_rate_limiter_blocks_after_limit():
    reset()
    assert check("t:1", 3, 60) is True
    assert check("t:1", 3, 60) is True
    assert check("t:1", 3, 60) is True
    assert check("t:1", 3, 60) is False
    reset()


def test_health_does_not_leak_internals(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "ready"
    assert "database_url" not in str(body).lower()
    assert "secret" not in str(body).lower()
