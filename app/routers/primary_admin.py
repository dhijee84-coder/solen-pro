from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..dependencies import require_roles

router = APIRouter(prefix="/api/primary-admin", tags=["primary-admin"])
primary_only = require_roles(models.RoleName.PRIMARY_ADMIN)


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: models.User = Depends(primary_only)):
    super_admins = db.query(models.User).filter(models.User.role == models.RoleName.SUPER_ADMIN).all()
    admins = db.query(models.User).filter(models.User.role == models.RoleName.ADMIN).all()
    recent_role_changes = db.query(models.AuditLog).filter(
        models.AuditLog.action.in_(["ROLE_CHANGED", "ADMIN_CREATED", "ADMIN_REMOVED", "ADMIN_EDITED"])
    ).order_by(models.AuditLog.timestamp.desc()).limit(20).all()

    return {
        "total_super_admins": len(super_admins),
        "total_admins": len(admins),
        "active_admins": sum(1 for a in admins if a.is_active),
        "inactive_admins": sum(1 for a in admins if not a.is_active),
        "active_super_admins": sum(1 for a in super_admins if a.is_active),
        "recent_role_changes": [{
            "action": a.action, "entity_id": a.entity_id, "new_value": a.new_value,
            "timestamp": a.timestamp.isoformat(),
        } for a in recent_role_changes],
        "totals": {
            "users": db.query(models.User).count(),
            "clients": db.query(models.ClientProfile).count(),
            "projects": db.query(models.Project).count(),
            "panels": db.query(models.Panel).count(),
            "payments": db.query(models.Payment).count(),
        },
    }
