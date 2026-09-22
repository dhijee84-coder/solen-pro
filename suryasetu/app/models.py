import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def gen_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def now():
    return datetime.utcnow()


# ── enums ──────────────────────────────────────────────────────────────

class RoleName(str, enum.Enum):
    PRIMARY_ADMIN = "PRIMARY_ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    CLIENT = "CLIENT"


class ProjectStatus(str, enum.Enum):
    PLANNING = "PLANNING"
    SITE_PREPARATION = "SITE_PREPARATION"
    ACTIVE = "ACTIVE"
    NEAR_CAPACITY = "NEAR_CAPACITY"
    FULL = "FULL"
    MAINTENANCE = "MAINTENANCE"
    CLOSED = "CLOSED"


class PanelStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    ALLOCATED = "ALLOCATED"
    INSTALLED = "INSTALLED"
    MAINTENANCE = "MAINTENANCE"
    DAMAGED = "DAMAGED"
    DECOMMISSIONED = "DECOMMISSIONED"


class StageStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAYMENT_DUE = "PAYMENT_DUE"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"


class DocumentType(str, enum.Enum):
    PAN = "PAN"
    AADHAAR = "AADHAAR"
    ELECTRICITY_BILL = "ELECTRICITY_BILL"
    ADDRESS_PROOF = "ADDRESS_PROOF"
    AGREEMENT = "AGREEMENT"
    PAYMENT_RECEIPT = "PAYMENT_RECEIPT"
    PROJECT_DOCUMENT = "PROJECT_DOCUMENT"
    INSTALLATION_DOCUMENT = "INSTALLATION_DOCUMENT"
    WARRANTY = "WARRANTY"
    OTHER = "OTHER"


class DocumentStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ServiceRequestStatus(str, enum.Enum):
    REQUESTED = "REQUESTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    QUOTED = "QUOTED"
    APPROVED = "APPROVED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_CLIENT = "WAITING_FOR_CLIENT"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class ContactType(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    WHATSAPP = "WHATSAPP"


class WarrantyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    VOID = "VOID"
    CLAIM_IN_PROGRESS = "CLAIM_IN_PROGRESS"
    CLAIM_APPROVED = "CLAIM_APPROVED"
    CLAIM_REJECTED = "CLAIM_REJECTED"


class WarrantyClaimStatus(str, enum.Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REPLACEMENT_REQUIRED = "REPLACEMENT_REQUIRED"
    REPLACED = "REPLACED"
    REPAIRED = "REPAIRED"
    CLOSED = "CLOSED"


class EnquiryStatus(str, enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    RESPONDED = "RESPONDED"
    CLOSED = "CLOSED"
    SPAM = "SPAM"


# ── auth / users / rbac ──────────────────────────────────────────────

class Permission(Base):
    __tablename__ = "permissions"
    id = Column(Integer, primary_key=True)
    code = Column(String(64), unique=True, nullable=False)  # e.g. "clients.view"
    description = Column(String(255), default="")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    id = Column(Integer, primary_key=True)
    role = Column(Enum(RoleName), nullable=False)
    permission_id = Column(Integer, ForeignKey("permissions.id"), nullable=False)
    permission = relationship("Permission")
    __table_args__ = (UniqueConstraint("role", "permission_id", name="uq_role_permission"),)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=lambda: gen_id("U"))
    role = Column(Enum(RoleName), nullable=False, default=RoleName.CLIENT)
    full_name = Column(String(150), nullable=False)
    phone = Column(String(15), unique=True, nullable=True, index=True)
    email = Column(String(150), unique=True, nullable=True, index=True)
    username = Column(String(80), unique=True, nullable=True, index=True)  # for admin-tier logins
    hashed_password = Column(String(255), nullable=True)  # null for OTP-only clients
    is_active = Column(Boolean, default=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    client_profile = relationship("ClientProfile", back_populates="user", uselist=False,
                                   foreign_keys="ClientProfile.user_id")
    notification_contacts = relationship("NotificationContact", back_populates="user",
                                          foreign_keys="NotificationContact.user_id")


class ClientProfile(Base):
    __tablename__ = "client_profiles"
    id = Column(String, primary_key=True, default=lambda: gen_id("C"))
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = Column(String(20), nullable=True)
    address = Column(Text, default="")
    city = Column(String(80), default="")
    state = Column(String(80), default="")
    pincode = Column(String(10), default="")

    kyc_status = Column(String(20), default="PENDING")  # PENDING / VERIFIED
    pan_number = Column(String(10), nullable=True)
    pan_name = Column(String(150), nullable=True)
    pan_verified_at = Column(DateTime, nullable=True)
    aadhaar_masked = Column(String(20), nullable=True)
    aadhaar_verified_at = Column(DateTime, nullable=True)

    onboarding_stage = Column(String(30), default="REGISTERED")
    # REGISTERED -> KYC_DONE -> BILL_UPLOADED -> PROJECT_ASSIGNED -> ACTIVE

    assigned_admin_id = Column(String, ForeignKey("users.id"), nullable=True)

    # client visibility toggles (section 57)
    show_generation = Column(Boolean, default=True)
    show_payments = Column(Boolean, default=True)
    show_project = Column(Boolean, default=True)
    show_panels = Column(Boolean, default=True)
    show_documents = Column(Boolean, default=True)
    show_services = Column(Boolean, default=True)
    show_support = Column(Boolean, default=True)
    show_notifications = Column(Boolean, default=True)

    admin_notes = Column(Text, default="")

    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    user = relationship("User", back_populates="client_profile", foreign_keys=[user_id])
    electricity_connection = relationship("ElectricityConnection", back_populates="client", uselist=False)
    client_project = relationship("ClientProject", back_populates="client", uselist=False)
    documents = relationship("Document", back_populates="client")
    payments = relationship("Payment", back_populates="client")
    service_requests = relationship("ClientServiceRequest", back_populates="client")
    tickets = relationship("SupportTicket", back_populates="client")


class ElectricityConnection(Base):
    __tablename__ = "electricity_connections"
    id = Column(String, primary_key=True, default=lambda: gen_id("EC"))
    client_id = Column(String, ForeignKey("client_profiles.id"), unique=True, nullable=False)
    rr_number = Column(String(40), nullable=True)
    discom = Column(String(80), default="")
    division = Column(String(120), default="")
    service_address = Column(Text, default="")
    tariff = Column(String(80), default="")
    sanctioned_load_kw = Column(Float, default=0)
    avg_monthly_units = Column(Float, default=0)
    avg_monthly_bill = Column(Float, default=0)
    phase = Column(String(20), default="Single phase")
    bill_file_path = Column(String(255), nullable=True)

    proposed_kw = Column(Float, default=0)
    system_cost = Column(Float, default=0)
    subsidy_estimate = Column(Float, default=0)
    payable_amount = Column(Float, default=0)

    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    client = relationship("ClientProfile", back_populates="electricity_connection")


# ── projects / panels ─────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=lambda: gen_id("PRJ"))
    project_code = Column(String(40), unique=True, nullable=False)
    project_name = Column(String(150), nullable=False)
    site_name = Column(String(150), default="")
    location = Column(String(150), default="")
    address = Column(Text, default="")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    capacity_kw = Column(Float, default=0)
    total_panels = Column(Integer, default=0)
    panel_capacity_kw = Column(Float, default=0.4)
    status = Column(Enum(ProjectStatus), default=ProjectStatus.PLANNING)
    commissioning_date = Column(String(20), nullable=True)
    is_public = Column(Boolean, default=False)
    public_description = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    panels = relationship("Panel", back_populates="project")

    @property
    def allocated_panels(self):
        return sum(1 for p in self.panels if p.status != PanelStatus.AVAILABLE and p.status != PanelStatus.DECOMMISSIONED)

    @property
    def available_panels(self):
        return sum(1 for p in self.panels if p.status == PanelStatus.AVAILABLE)

    @property
    def utilization(self):
        if not self.total_panels:
            return 0.0
        return round(self.allocated_panels / self.total_panels, 4)


class Panel(Base):
    __tablename__ = "panels"
    id = Column(String, primary_key=True, default=lambda: gen_id("PNL"))
    serial_number = Column(String(60), unique=True, nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    manufacturer = Column(String(80), default="")
    model = Column(String(80), default="")
    watt_rating = Column(Integer, default=400)
    status = Column(Enum(PanelStatus), default=PanelStatus.AVAILABLE, index=True)
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=True, index=True)
    installation_date = Column(String(20), nullable=True)
    purchase_date = Column(String(20), nullable=True)
    warranty_start_date = Column(String(20), nullable=True)
    warranty_end_date = Column(String(20), nullable=True)
    warranty_type = Column(String(60), default="MANUFACTURER")  # MANUFACTURER / EXTENDED / SERVICE
    warranty_provider = Column(String(120), default="")
    warranty_terms = Column(Text, default="")
    warranty_years = Column(Integer, default=25)
    added_sequence = Column(Integer, nullable=False)  # monotonically increasing -> FIFO order
    created_at = Column(DateTime, default=now)

    project = relationship("Project", back_populates="panels")
    warranty_claims = relationship("WarrantyClaim", back_populates="panel")

    def computed_warranty_status(self, expiring_days: int = 90) -> str:
        """Backend-calculated warranty status. Never trust frontend for this."""
        if not self.warranty_end_date:
            return WarrantyStatus.VOID.value
        try:
            from datetime import datetime as dt, timedelta
            end = dt.strptime(self.warranty_end_date[:10], "%Y-%m-%d").date()
            today = dt.utcnow().date()
            if end < today:
                return WarrantyStatus.EXPIRED.value
            if end <= today + timedelta(days=expiring_days):
                return WarrantyStatus.EXPIRING_SOON.value
            return WarrantyStatus.ACTIVE.value
        except Exception:
            return WarrantyStatus.VOID.value


class ClientProject(Base):
    """A client's assignment to a project, aggregating their allocated panel set."""
    __tablename__ = "client_projects"
    id = Column(String, primary_key=True, default=lambda: gen_id("CP"))
    client_id = Column(String, ForeignKey("client_profiles.id"), unique=True, nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    allocated_panel_count = Column(Integer, default=0)
    allocated_capacity_kw = Column(Float, default=0)
    contract_total = Column(Float, default=0)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    client = relationship("ClientProfile", back_populates="client_project")
    project = relationship("Project")


class ProjectStage(Base):
    """One of the six standard install stages, instantiated per client project."""
    __tablename__ = "project_stages"
    id = Column(String, primary_key=True, default=lambda: gen_id("STG"))
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False)
    stage_name = Column(String(150), nullable=False)
    percentage = Column(Float, nullable=False)
    status = Column(Enum(StageStatus), default=StageStatus.NOT_STARTED)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    completed_by = Column(String, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, default="")
    payment_required = Column(Boolean, default=True)
    payment_status = Column(String(20), default="NOT_DUE")  # NOT_DUE / DUE / PAID


# ── payments ────────────────────────────────────────────────────────

class Payment(Base):
    __tablename__ = "payments"
    id = Column(String, primary_key=True, default=lambda: gen_id("PAY"))
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    service_id = Column(String, ForeignKey("client_service_requests.id"), nullable=True)
    stage_id = Column(String, ForeignKey("project_stages.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(6), default="INR")
    payment_method = Column(String(40), default="UPI")
    transaction_reference = Column(String(60), unique=True, nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    created_at = Column(DateTime, default=now)
    paid_at = Column(DateTime, nullable=True)
    recorded_by = Column(String, ForeignKey("users.id"), nullable=True)
    is_first_payment = Column(Boolean, default=False)

    client = relationship("ClientProfile", back_populates="payments")


# ── documents ───────────────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"
    id = Column(String, primary_key=True, default=lambda: gen_id("DOC"))
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=False, index=True)
    document_type = Column(Enum(DocumentType), default=DocumentType.OTHER)
    original_filename = Column(String(255), default="")
    stored_filename = Column(String(255), default="")
    file_path = Column(String(500), default="")
    mime_type = Column(String(80), default="")
    file_size = Column(Integer, default=0)
    uploaded_by = Column(String, ForeignKey("users.id"), nullable=True)
    uploaded_at = Column(DateTime, default=now)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.UPLOADED)
    verified_by = Column(String, ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    notes = Column(Text, default="")

    client = relationship("ClientProfile", back_populates="documents")


# ── services / support ─────────────────────────────────────────────

class Service(Base):
    __tablename__ = "services"
    id = Column(String, primary_key=True, default=lambda: gen_id("SVC"))
    name = Column(String(120), nullable=False)
    description = Column(Text, default="")
    base_price = Column(Float, default=0)
    is_active = Column(Boolean, default=True)


class ClientServiceRequest(Base):
    __tablename__ = "client_service_requests"
    id = Column(String, primary_key=True, default=lambda: gen_id("SR"))
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=False, index=True)
    service_id = Column(String, ForeignKey("services.id"), nullable=False)
    status = Column(Enum(ServiceRequestStatus), default=ServiceRequestStatus.REQUESTED)
    quoted_price = Column(Float, nullable=True)
    notes = Column(Text, default="")
    assigned_admin_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    client = relationship("ClientProfile", back_populates="service_requests")
    service = relationship("Service")


class SupportTicket(Base):
    __tablename__ = "support_tickets"
    id = Column(String, primary_key=True, default=lambda: gen_id("TCK"))
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=False, index=True)
    subject = Column(String(200), nullable=False)
    category = Column(String(60), default="GENERAL")
    description = Column(Text, default="")
    priority = Column(String(20), default="NORMAL")
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN)
    assigned_admin_id = Column(String, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    client = relationship("ClientProfile", back_populates="tickets")
    messages = relationship("TicketMessage", back_populates="ticket")


class TicketMessage(Base):
    __tablename__ = "ticket_messages"
    id = Column(String, primary_key=True, default=lambda: gen_id("MSG"))
    ticket_id = Column(String, ForeignKey("support_tickets.id"), nullable=False)
    sender_user_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=now)

    ticket = relationship("SupportTicket", back_populates="messages")


# ── notifications ───────────────────────────────────────────────────

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String, primary_key=True, default=lambda: gen_id("NTF"))
    recipient_user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    type = Column(String(40), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, default="")
    priority = Column(String(20), default="NORMAL")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)
    related_entity = Column(String(60), nullable=True)
    related_entity_id = Column(String(60), nullable=True)


class NotificationContact(Base):
    __tablename__ = "notification_contacts"
    id = Column(String, primary_key=True, default=lambda: gen_id("NC"))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(ContactType), nullable=False)
    value = Column(String(150), nullable=False)
    label = Column(String(60), default="")
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)

    user = relationship("User", back_populates="notification_contacts")


# ── generation ──────────────────────────────────────────────────────

class GenerationRecord(Base):
    __tablename__ = "generation_records"
    id = Column(String, primary_key=True, default=lambda: gen_id("GEN"))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=True, index=True)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    generation_kwh = Column(Float, default=0)
    allocated_generation_kwh = Column(Float, default=0)
    peak_kw = Column(Float, default=0)
    co2_saved_kg = Column(Float, default=0)

    __table_args__ = (UniqueConstraint("client_id", "date", name="uq_client_date"),)


# ── audit / settings / CMS ─────────────────────────────────────────

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String, primary_key=True, default=lambda: gen_id("AUD"))
    actor_user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(60), nullable=False)
    entity_type = Column(String(60), default="")
    entity_id = Column(String(60), default="")
    old_value = Column(Text, default="")
    new_value = Column(Text, default="")
    ip_address = Column(String(60), default="")
    timestamp = Column(DateTime, default=now, index=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"
    key = Column(String(80), primary_key=True)
    value = Column(Text, default="")


class WebsiteContent(Base):
    __tablename__ = "website_content"
    key = Column(String(80), primary_key=True)
    value = Column(Text, default="")


class WarrantyClaim(Base):
    __tablename__ = "warranty_claims"
    id = Column(String, primary_key=True, default=lambda: gen_id("WC"))
    panel_id = Column(String, ForeignKey("panels.id"), nullable=False, index=True)
    client_id = Column(String, ForeignKey("client_profiles.id"), nullable=False, index=True)
    issue_summary = Column(String(200), nullable=False)
    description = Column(Text, default="")
    date_discovered = Column(String(20), nullable=True)
    contact_phone = Column(String(20), default="")
    contact_email = Column(String(150), default="")
    status = Column(Enum(WarrantyClaimStatus), default=WarrantyClaimStatus.SUBMITTED, index=True)
    assigned_admin_id = Column(String, ForeignKey("users.id"), nullable=True)
    resolution_notes = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)

    panel = relationship("Panel", back_populates="warranty_claims")
    client = relationship("ClientProfile")


class ContactEnquiry(Base):
    __tablename__ = "contact_enquiries"
    id = Column(String, primary_key=True, default=lambda: gen_id("ENQ"))
    name = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    phone = Column(String(20), default="")
    subject = Column(String(200), default="")
    message = Column(Text, nullable=False)
    status = Column(Enum(EnquiryStatus), default=EnquiryStatus.NEW, index=True)
    assigned_admin_id = Column(String, ForeignKey("users.id"), nullable=True)
    internal_notes = Column(Text, default="")
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class FAQ(Base):
    __tablename__ = "faqs"
    id = Column(String, primary_key=True, default=lambda: gen_id("FAQ"))
    question = Column(String(400), nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String(80), default="GENERAL")
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class Announcement(Base):
    __tablename__ = "announcements"
    id = Column(String, primary_key=True, default=lambda: gen_id("ANN"))
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    cta_text = Column(String(80), default="")
    cta_url = Column(String(300), default="")
    start_date = Column(String(20), nullable=True)
    end_date = Column(String(20), nullable=True)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)
