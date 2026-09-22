"""Consistent API error responses. Production never includes stack traces."""
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .logging_config import logger


def _detail_from_validation(exc: RequestValidationError) -> str:
    parts = []
    for err in exc.errors()[:6]:
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        msg = err.get("msg", "invalid")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts) or "Invalid request."


def install_error_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exc(request: Request, exc: StarletteHTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(status_code=exc.status_code, content={"detail": detail, "success": False})

    @app.exception_handler(RequestValidationError)
    async def validation_exc(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": _detail_from_validation(exc), "success": False})

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        if isinstance(exc, HTTPException):
            detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
            return JSONResponse(status_code=exc.status_code, content={"detail": detail, "success": False})
        logger.exception("unhandled_error path=%s", request.url.path)
        if settings.is_debug:
            return JSONResponse(status_code=500, content={"detail": str(exc), "success": False})
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again.", "success": False},
        )
