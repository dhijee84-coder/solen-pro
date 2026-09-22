"""Secure local file storage for documents, branding and warranty attachments.

Development stores files under uploads/. Production can point UPLOAD_DIR at a
persistent volume. Object storage (S3) is a documented extension point — do
not put provider secrets in source.
"""
import os
import re
import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile

from ..config import settings

ALLOWED_DOCUMENT_MIME = {
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
ALLOWED_DOCUMENT_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
FORBIDDEN_EXT = {
    ".exe", ".sh", ".bat", ".cmd", ".com", ".js", ".mjs", ".html", ".htm",
    ".php", ".phtml", ".svg", ".xml", ".py", ".rb", ".pl", ".cgi", ".jar",
    ".wasm", ".dll", ".so",
}
ALLOWED_BRAND_MIME = {
    "image/png", "image/jpeg", "image/webp", "image/svg+xml",
    "image/x-icon", "image/vnd.microsoft.icon",
}


def _ext(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def sanitize_filename(filename: str) -> str:
    normalized = (filename or "upload").replace("\\", "/")
    base = os.path.basename(normalized)
    base = base.replace("..", "_")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base)
    base = base.lstrip("._")
    return (base or "upload")[:120]


def assert_under_upload_dir(path: str) -> str:
    root = os.path.abspath(settings.upload_dir)
    full = os.path.abspath(path)
    if full != root and not full.startswith(root + os.sep):
        raise HTTPException(400, "Invalid file path.")
    return full


def validate_document_upload(file: UploadFile, data: bytes):
    if not data:
        raise HTTPException(400, "Empty file.")
    if len(data) > settings.max_upload_bytes:
        mb = settings.max_upload_bytes // (1024 * 1024)
        raise HTTPException(400, f"File too large (max {mb} MB).")
    ext = _ext(file.filename or "")
    if ext in FORBIDDEN_EXT:
        raise HTTPException(400, "This file type is not allowed.")
    if ext not in ALLOWED_DOCUMENT_EXT:
        raise HTTPException(400, "Only PDF, JPEG, PNG or WebP documents are accepted.")
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype and ctype not in ALLOWED_DOCUMENT_MIME and ctype != "application/octet-stream":
        raise HTTPException(400, "Only PDF, JPEG, PNG or WebP documents are accepted.")
    # Reject obvious executable magic bytes
    if data[:2] == b"MZ" or data[:4] == b"\x7fELF":
        raise HTTPException(400, "This file type is not allowed.")


def store_bytes(relative_dir: str, original_filename: str, data: bytes) -> tuple[str, str, int]:
    """Write bytes under upload_dir/relative_dir. Returns (abs_path, stored_name, size)."""
    safe = sanitize_filename(original_filename)
    ext = _ext(safe) or ".bin"
    stored = f"{datetime.utcnow().strftime('%Y%m%dT%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    dest_dir = os.path.join(settings.upload_dir, relative_dir)
    os.makedirs(dest_dir, exist_ok=True)
    dest = assert_under_upload_dir(os.path.join(dest_dir, stored))
    with open(dest, "wb") as out:
        out.write(data)
    return dest, stored, len(data)
