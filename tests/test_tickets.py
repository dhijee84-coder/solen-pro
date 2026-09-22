from fastapi.testclient import TestClient

from app.main import app
from app import models
from app.database import SessionLocal
from tests.conftest import register_client, make_staff, login_staff


def test_ticket_conversation_end_to_end():
    client_api = TestClient(app)
    register_client(client_api, "9845500001", "Ticket Client")
    created = client_api.post("/api/client/tickets", json={
        "subject": "Inverter alarm",
        "category": "TECHNICAL",
        "description": "Red light flashing since morning.",
        "priority": "HIGH",
    })
    assert created.status_code == 200
    ticket_id = created.json()["ticket_id"]

    staff = TestClient(app)
    db = SessionLocal()
    make_staff(db, models.RoleName.ADMIN, "ticketadmin")
    db.close()
    login_staff(staff, "ticketadmin")
    listed = staff.get("/api/admin/tickets").json()
    assert any(t["id"] == ticket_id for t in listed)

    reply = staff.post(f"/api/admin/tickets/{ticket_id}/messages", json={"message": "We will inspect tomorrow."})
    assert reply.status_code == 200

    detail = client_api.get(f"/api/client/tickets/{ticket_id}").json()
    assert any("inspect tomorrow" in m["message"] for m in detail["messages"])

    client_api.post(f"/api/client/tickets/{ticket_id}/messages", json={"message": "Thank you, afternoon works."})
    staff_detail = staff.get(f"/api/admin/tickets/{ticket_id}").json()
    assert any("afternoon works" in m["message"] for m in staff_detail["messages"])


def test_unauthorized_ticket_access_is_rejected():
    a = TestClient(app)
    b = TestClient(app)
    register_client(a, "9845500002", "A")
    register_client(b, "9845500003", "B")
    ticket_id = a.post("/api/client/tickets", json={
        "subject": "Private", "category": "GENERAL", "description": "Do not show this to B please.", "priority": "NORMAL",
    }).json()["ticket_id"]
    assert b.get(f"/api/client/tickets/{ticket_id}").status_code == 404
    anon = TestClient(app)
    assert anon.get(f"/api/client/tickets/{ticket_id}").status_code == 401
    assert anon.get("/api/admin/tickets").status_code == 401
