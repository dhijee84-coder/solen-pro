from sqlalchemy.orm import Session

from .. import models
from .notifiers import email_notifier, whatsapp_notifier, sms_notifier


def _dispatch_external(db: Session, user: models.User, title: str, message: str):
    contacts = db.query(models.NotificationContact).filter(
        models.NotificationContact.user_id == user.id,
        models.NotificationContact.is_active == True,  # noqa: E712
    ).all()
    for c in contacts:
        if c.type == models.ContactType.EMAIL:
            email_notifier.send(c.value, title, message)
        elif c.type == models.ContactType.WHATSAPP:
            whatsapp_notifier.send(c.value, title, message)
        elif c.type == models.ContactType.PHONE:
            sms_notifier.send(c.value, title, message)


def notify_user(db: Session, user: models.User, type_: str, title: str, message: str,
                 priority: str = "NORMAL", related_entity: str = None, related_entity_id: str = None):
    n = models.Notification(
        recipient_user_id=user.id, type=type_, title=title, message=message,
        priority=priority, related_entity=related_entity, related_entity_id=related_entity_id,
    )
    db.add(n)
    _dispatch_external(db, user, title, message)
    return n


def _admins_and_super_admins(db: Session):
    return db.query(models.User).filter(
        models.User.role.in_([models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN]),
        models.User.is_active == True,  # noqa: E712
    ).all()


def _admins_super_admins_and_primary(db: Session):
    return db.query(models.User).filter(
        models.User.role.in_([models.RoleName.ADMIN, models.RoleName.SUPER_ADMIN, models.RoleName.PRIMARY_ADMIN]),
        models.User.is_active == True,  # noqa: E712
    ).all()


def notify_new_client(db: Session, client: models.ClientProfile):
    title = "New client registered"
    msg = (f"{client.user.full_name} ({client.id}) registered. "
           f"Phone {client.user.phone or '-'}, email {client.user.email or '-'}. "
           f"KYC status: {client.kyc_status}.")
    for u in _admins_and_super_admins(db):
        notify_user(db, u, "NEW_CLIENT", title, msg, related_entity="client", related_entity_id=client.id)


def notify_first_payment(db: Session, payment: models.Payment):
    title = "First payment received"
    msg = (f"Client {payment.client.user.full_name} ({payment.client_id}) made their first payment: "
           f"₹{payment.amount:,.0f} via {payment.payment_method}, txn {payment.transaction_reference}.")
    for u in _admins_and_super_admins(db):
        notify_user(db, u, "FIRST_PAYMENT", title, msg, related_entity="payment", related_entity_id=payment.id)


def notify_project_capacity(db: Session, project: models.Project, level: str):
    """level: WARNING | CRITICAL | FULL"""
    util_pct = round(project.utilization * 100, 1)
    if level == "FULL":
        title = "Project full"
        msg = (f"{project.project_name} ({project.project_code}) has reached 100% panel allocation. "
               f"New client allocations must not be assigned to this project. "
               f"Create or activate another project.")
        ntype = "PROJECT_FULL"
    elif level == "CRITICAL":
        title = "Solar project capacity alert — critical"
        msg = (f"{project.project_name}: {project.allocated_panels}/{project.total_panels} panels allocated "
               f"({util_pct}%). This project is approaching full allocation. Prepare a new project site.")
        ntype = "PROJECT_CAPACITY_CRITICAL"
    else:
        title = "Solar project capacity alert — warning"
        msg = (f"{project.project_name}: {project.allocated_panels}/{project.total_panels} panels allocated "
               f"({util_pct}%). Utilization has crossed the warning threshold.")
        ntype = "PROJECT_CAPACITY_WARNING"

    for u in _admins_super_admins_and_primary(db):
        notify_user(db, u, ntype, title, msg, priority="HIGH", related_entity="project", related_entity_id=project.id)


def notify_client_question(db: Session, ticket: models.SupportTicket):
    title = "New client question"
    msg = f"Ticket {ticket.id} from {ticket.client.user.full_name}: {ticket.subject}"
    recipients = _admins_and_super_admins(db)
    for u in recipients:
        notify_user(db, u, "CLIENT_QUESTION", title, msg, related_entity="ticket", related_entity_id=ticket.id)


def notify_service_request(db: Session, sr: models.ClientServiceRequest):
    title = "New service request"
    msg = f"{sr.client.user.full_name} requested service: {sr.service.name}"
    for u in _admins_and_super_admins(db):
        notify_user(db, u, "SERVICE_REQUEST", title, msg, related_entity="service_request", related_entity_id=sr.id)
