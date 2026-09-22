from app import models
from app.database import SessionLocal
from app.services.export_service import to_csv, _sanitize_cell
from tests.conftest import make_staff, login_staff


def test_authorized_csv_export_works(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.SUPER_ADMIN, "exporter")
    db.close()
    login_staff(client, "exporter")
    r = client.get("/api/admin/export/clients")
    assert r.status_code == 200
    assert "text/csv" in r.headers.get("content-type", "")
    body = r.content.decode("utf-8")
    assert "id" in body.split("\n")[0]


def test_unauthorized_csv_export_returns_403(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "noexport")
    db.close()
    login_staff(client, "noexport")
    assert client.get("/api/admin/export/clients").status_code == 403
    assert client.get("/api/admin/export/payments").status_code == 403
    assert client.get("/api/admin/export/panels").status_code == 403


def test_csv_formula_injection_is_sanitized():
    assert _sanitize_cell("=1+1").startswith("'")
    assert _sanitize_cell("+cmd").startswith("'")
    assert _sanitize_cell("-2+2").startswith("'")
    assert _sanitize_cell("@SUM(A1)").startswith("'")
    assert _sanitize_cell("normal") == "normal"
    csv = to_csv(["name"], [["=cmd|' /C calc'!A0"]])
    assert "=cmd" not in csv.split("\n")[1] or csv.split("\n")[1].startswith("'") or csv.split("\n")[1].startswith('"\'')


def test_export_is_audited(client):
    db = SessionLocal()
    make_staff(db, models.RoleName.PRIMARY_ADMIN, "auditor")
    db.close()
    login_staff(client, "auditor")
    assert client.get("/api/admin/export/payments").status_code == 200
    db = SessionLocal()
    logs = db.query(models.AuditLog).filter(models.AuditLog.action == "EXPORT_CSV").all()
    assert logs
    assert any(l.entity_type == "payments" for l in logs)
    db.close()
