from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from .database import get_db
from .models import RoleName, User
from .permissions import role_has_permission
from .security import decode_access_token


def _extract_token(access_token: Optional[str], authorization: Optional[str]) -> Optional[str]:
    if access_token:
        return access_token
    if authorization and authorization.lower().startswith("bearer "):
        return authorization.split(" ", 1)[1]
    return None


def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(access_token, authorization)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired session")
    user = db.query(User).filter(User.id == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account not found or inactive")
    return user


def get_optional_user(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not access_token:
        return None
    payload = decode_access_token(access_token)
    if not payload:
        return None
    return db.query(User).filter(User.id == payload.get("sub")).first()


def require_roles(*roles: RoleName):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for this action")
        return user
    return _dep


def require_permission(code: str):
    def _dep(user: User = Depends(get_current_user)) -> User:
        if not role_has_permission(user.role, code):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {code}")
        return user
    return _dep
