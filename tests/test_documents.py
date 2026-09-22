from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import register_client, make_staff, login_staff

MINI_PDF = b"%PDF-1.1\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


def test_client_can_access_own_documents(client):
    register_client(client, "9845300001", "Doc Owner")
    r = client.post(
        "/api/client/documents/upload",
        data={"document_type": "PAN"},
        files={"file": ("pan.pdf", MINI_PDF, "application/pdf")},
    )
    assert r.status_code == 200, r.text
    doc_id = r.json()["document_id"]
    listed = client.get("/api/client/documents").json()
    assert any(d["id"] == doc_id for d in listed)
    dl = client.get(f"/api/client/documents/{doc_id}/file")
    assert dl.status_code == 200
    assert dl.content.startswith(b"%PDF")


def test_client_cannot_access_another_clients_documents():
    a = TestClient(app)
    b = TestClient(app)
    register_client(a, "9845300002", "Owner")
    register_client(b, "9845300003", "Stranger")
    doc_id = a.post(
        "/api/client/documents/upload",
        data={"document_type": "AADHAAR"},
        files={"file": ("aadhaar.pdf", MINI_PDF, "application/pdf")},
    ).json()["document_id"]
    assert b.get(f"/api/client/documents/{doc_id}/file").status_code == 404
    listed = b.get("/api/client/documents").json()
    assert all(d["id"] != doc_id for d in listed)


def test_unauthorized_document_access_is_rejected(client):
    register_client(client, "9845300004", "Owner")
    doc_id = client.post(
        "/api/client/documents/upload",
        data={"document_type": "PAN"},
        files={"file": ("pan.pdf", MINI_PDF, "application/pdf")},
    ).json()["document_id"]
    anon = TestClient(app)
    assert anon.get(f"/api/client/documents/{doc_id}/file").status_code == 401
    assert anon.get("/api/admin/documents").status_code == 401


def test_executable_upload_rejected(client):
    register_client(client, "9845300005", "Hacker")
    r = client.post(
        "/api/client/documents/upload",
        data={"document_type": "OTHER"},
        files={"file": ("payload.exe", b"MZ\x90\x00fake", "application/octet-stream")},
    )
    assert r.status_code == 400


def test_path_traversal_filename_is_sanitized(client):
    register_client(client, "9845300006", "Trav")
    r = client.post(
        "/api/client/documents/upload",
        data={"document_type": "OTHER"},
        files={"file": ("../../etc/passwd.pdf", MINI_PDF, "application/pdf")},
    )
    assert r.status_code == 200
    listed = client.get("/api/client/documents").json()
    assert listed
    assert ".." not in (listed[0].get("filename") or "")
