from datetime import datetime
import random
import string

from sqlalchemy.orm import Session

from .. import models
from . import notification_service
from .audit_service import log_action


def _gen_txn_ref() -> str:
    return "SS" + "".join(random.choices(string.digits, k=9))


def record_payment(db: Session, client: models.ClientProfile, amount: float, method: str,
                    actor: models.User, stage_id: str = None, service_id: str = None) -> models.Payment:
    is_first = db.query(models.Payment).filter(
        models.Payment.client_id == client.id, models.Payment.status == models.PaymentStatus.SUCCESS
    ).count() == 0

    payment = models.Payment(
        client_id=client.id,
        project_id=client.client_project.project_id if client.client_project else None,
        stage_id=stage_id,
        service_id=service_id,
        amount=amount,
        payment_method=method,
        transaction_reference=_gen_txn_ref(),
        status=models.PaymentStatus.SUCCESS,
        paid_at=datetime.utcnow(),
        recorded_by=actor.id if actor else None,
        is_first_payment=is_first,
    )
    db.add(payment)

    if stage_id:
        stage = db.query(models.ProjectStage).filter(models.ProjectStage.id == stage_id).first()
        if stage:
            stage.status = models.StageStatus.COMPLETED
            stage.payment_status = "PAID"
            stage.completed_at = datetime.utcnow()
            stage.completed_by = actor.id if actor else None
            nxt = db.query(models.ProjectStage).filter(
                models.ProjectStage.client_id == client.id,
                models.ProjectStage.stage_number == stage.stage_number + 1,
            ).first()
            if nxt and nxt.status == models.StageStatus.NOT_STARTED:
                nxt.status = models.StageStatus.IN_PROGRESS
                nxt.started_at = datetime.utcnow()

    log_action(db, actor, "PAYMENT_RECORDED", entity_type="client", entity_id=client.id,
               new_value=f"amount={amount} method={method} txn={payment.transaction_reference}")

    db.commit()
    db.refresh(payment)

    if is_first:
        notification_service.notify_first_payment(db, payment)
        db.commit()

    return payment
