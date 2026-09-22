import secrets

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from sqlalchemy.orm import Session

from .. import models, schemas
from ..config import settings
from ..database import get_db
from ..security import create_access_token, verify_password, set_auth_cookie, clear_auth_cookie
from ..dependencies import get_current_user
from ..rate_limit import limiter
from ..services.audit_service import log_action
from ..services.notifiers import sms_notifier
from ..logging_config import logger

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory OTP store for a single-process server: {phone: code}.
_otp_store: dict[str, str] = {}


def _otp_phone_key(request: Request) -> str:
    try:
        return (request._json or {}).get("phone", "")  # type: ignore[attr-defined]
    except Exception:
        return ""


@router.post("/otp/send", dependencies=[Depends(limiter("otp_send", settings.rate_limit_otp))])
def send_otp(payload: schemas.OtpSendIn):
    phone = payload.phone.strip()
    if len(phone) != 10 or not phone.isdigit():
        raise HTTPException(400, "Enter a valid 10-digit mobile number.")
    if settings.allow_dev_otp:
        code = settings.dev_otp
    else:
        code = f"{secrets.randbelow(10000):04d}"
        sms_notifier.send(phone, "Solan OTP", "Your Solan verification code has been sent.")
    _otp_store[phone] = code
    logger.info("otp_sent", extra={"result": "ok", "endpoint": "/api/auth/otp/send"})
    body = {"success": True, "message": f"OTP sent to +91 {phone}."}
    if settings.expose_dev_otp:
        body["message"] = f"OTP sent to +91 {phone}. Development OTP is {code}."
        body["dev_otp"] = code
    return body


@router.post("/otp/verify", dependencies=[Depends(limiter("otp_verify", settings.rate_limit_otp))])
def verify_otp(payload: schemas.OtpVerifyIn, response: Response, db: Session = Depends(get_db)):
    phone = payload.phone.strip()
    if settings.allow_dev_otp:
        expected = _otp_store.get(phone, settings.dev_otp)
    else:
        expected = _otp_store.get(phone)
        if not expected:
            raise HTTPException(400, "That code does not match. Request a new OTP.")
    if payload.code != expected:
        raise HTTPException(400, "That code does not match. Check the SMS and try again.")
    _otp_store.pop(phone, None)

    user = db.query(models.User).filter(models.User.phone == phone).first()
    is_new = False
    if not user:
        is_new = True
        user = models.User(
            role=models.RoleName.CLIENT,
            full_name=(payload.full_name or "New Client").strip(),
            phone=phone,
        )
        db.add(user)
        db.flush()
        profile = models.ClientProfile(user_id=user.id)
        db.add(profile)
        db.flush()
        log_action(db, user, "CLIENT_CREATED", entity_type="user", entity_id=user.id)
        db.commit()
        db.refresh(user)

        from ..services import notification_service
        notify_target = db.query(models.ClientProfile).filter(models.ClientProfile.user_id == user.id).first()
        notification_service.notify_new_client(db, notify_target)
        db.commit()

    token = create_access_token(user.id, user.role.value)
    set_auth_cookie(response, token)
    return {
        "success": True,
        "is_new_client": is_new,
        "user": {"id": user.id, "name": user.full_name, "phone": user.phone, "role": user.role.value},
    }


@router.post("/admin/login", dependencies=[Depends(limiter("admin_login", settings.rate_limit_login))])
def admin_login(payload: schemas.AdminLoginIn, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        logger.info("admin_login_failed", extra={"result": "denied", "endpoint": "/api/auth/admin/login"})
        raise HTTPException(401, "Invalid username or password.")
    if user.role == models.RoleName.CLIENT:
        raise HTTPException(403, "Use the client sign-in flow.")
    if not user.is_active:
        raise HTTPException(403, "This account has been deactivated.")

    token = create_access_token(user.id, user.role.value)
    set_auth_cookie(response, token)
    log_action(db, user, "LOGIN", entity_type="user", entity_id=user.id)
    db.commit()
    return {"success": True, "user": {"id": user.id, "name": user.full_name, "role": user.role.value}}


@router.post("/logout")
def logout(response: Response):
    clear_auth_cookie(response)
    return {"success": True}


@router.get("/me")
def me(user: models.User = Depends(get_current_user)):
    return {"id": user.id, "name": user.full_name, "role": user.role.value, "phone": user.phone, "email": user.email}
