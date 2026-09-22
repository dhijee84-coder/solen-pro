from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.database import SessionLocal
from tests.conftest import register_client, make_staff, login_staff


def test_client_can_view_own_payments(client):
    register_client(client, "9845400001", "Payer")
    r = client.post("/api/client/payments/pay", json={"amount": 15000, "method": "UPI"})
    assert r.status_code == 200
    listed = client.get("/api/client/payments").json()
    assert len(listed) == 1
    assert listed[0]["amount"] == 15000
    assert listed[0]["status"] == "SUCCESS"


def test_client_cannot_view_another_clients_payments():
    a = TestClient(app)
    b = TestClient(app)
    register_client(a, "9845400002", "AlicePay")
    register_client(b, "9845400003", "BobPay")
    a.post("/api/client/payments/pay", json={"amount": 5000, "method": "UPI"})
    b.post("/api/client/payments/pay", json={"amount": 9000, "method": "CARD"})
    a_pays = a.get("/api/client/payments").json()
    b_pays = b.get("/api/client/payments").json()
    assert a_pays[0]["amount"] == 5000
    assert b_pays[0]["amount"] == 9000
    assert a_pays[0]["id"] != b_pays[0]["id"]


def test_unauthorized_payment_modification_is_rejected(client):
    register_client(client, "9845400004", "Payer")
    pay_id = client.post("/api/client/payments/pay", json={"amount": 1000, "method": "UPI"}).json()["payment_id"]
    # No client-facing payment mutation besides creating their own
    assert client.put(f"/api/client/payments/{pay_id}", json={"amount": 1}).status_code in (404, 405)
    assert client.delete(f"/api/client/payments/{pay_id}").status_code in (404, 405)
    anon = TestClient(app)
    assert anon.post("/api/client/payments/pay", json={"amount": 10, "method": "UPI"}).status_code == 401
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "payadmin")
    db.close()
    staff = TestClient(app)
    login_staff(staff, "payadmin")
    # Staff recording a payment requires a real client id; forged id is rejected
    r = staff.post("/api/admin/clients/C-DOESNOTEXIST/payments", json={"amount": 10, "method": "UPI"})
    assert r.status_code in (404, 400, 422)
