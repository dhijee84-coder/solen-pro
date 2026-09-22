import os
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine, SessionLocal, ensure_indexes
from .errors import install_error_handlers
from .logging_config import logger
from .routers import auth, client, admin, primary_admin, pages, public_api
from .security import decode_access_token

Base.metadata.create_all(bind=engine)
ensure_indexes(engine)

docs_url = "/docs" if settings.is_debug else None
redoc_url = "/redoc" if settings.is_debug else None
openapi_url = "/openapi.json" if settings.is_debug else None

app = FastAPI(
    title="Solan",
    description="Solar farm panel sales, operations and usage-based energy billing",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

install_error_handlers(app)

app.mount("/static", StaticFiles(directory="static"), name="static")
branding_dir = os.path.join(settings.upload_dir, "branding")
os.makedirs(branding_dir, exist_ok=True)
app.mount("/uploads/branding", StaticFiles(directory=branding_dir), name="branding")

app.include_router(pages.router)
app.include_router(auth.router)
app.include_router(client.router)
app.include_router(admin.router)
app.include_router(primary_admin.router)
app.include_router(public_api.router)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.time()
    response = await call_next(request)
    duration_ms = round((time.time() - start) * 1000, 1)
    user_id = None
    role = None
    token = request.cookies.get("access_token")
    if token:
        payload = decode_access_token(token)
        if payload:
            user_id = payload.get("sub")
            role = payload.get("role")
    logger.info(
        "request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "user_id": user_id,
            "role": role,
            "request_id": request_id,
            "endpoint": request.url.path,
            "result": "ok" if response.status_code < 400 else "error",
        },
    )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.on_event("startup")
def _startup_jobs():
    if settings.is_test:
        return
    db = SessionLocal()
    try:
        from .services import warranty_service
        n = warranty_service.scan_expiring_warranties(db)
        db.commit()
        if n:
            logger.info("startup_warranty_scan", extra={"result": n})
    except Exception:
        logger.exception("startup_warranty_scan_failed")
        db.rollback()
    finally:
        db.close()


@app.get("/health")
def health():
    """Liveness: process is up. Does not touch the database."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    """Readiness: database is reachable. No internals leaked."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        logger.exception("readiness_failed")
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/api/health")
def api_health():
    return {"status": "ok", "service": "suryasetu"}
