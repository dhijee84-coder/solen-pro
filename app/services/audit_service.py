from sqlalchemy.orm import Session

from .. import models


def log_action(db: Session, actor: models.User, action: str, entity_type: str = "",
                entity_id: str = "", old_value: str = "", new_value: str = "", ip_address: str = ""):
    entry = models.AuditLog(
        actor_user_id=actor.id if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        old_value=str(old_value),
        new_value=str(new_value),
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
