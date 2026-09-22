from typing import Optional
from pydantic import BaseModel, Field


class ClientRegisterIn(BaseModel):
    full_name: str
    phone: str = Field(min_length=10, max_length=10)


class OtpSendIn(BaseModel):
    phone: str


class OtpVerifyIn(BaseModel):
    phone: str
    code: str
    full_name: Optional[str] = None


class AdminLoginIn(BaseModel):
    username: str
    password: str


class PanVerifyIn(BaseModel):
    pan_number: str


class AadhaarVerifyIn(BaseModel):
    aadhaar_number: str


class BillDraftIn(BaseModel):
    rr_number: str
    discom: str = "BESCOM"
    division: str = ""
    service_address: str = ""
    tariff: str = "LT-2(a) Domestic"
    sanctioned_load_kw: float = 0
    avg_monthly_units: float
    phase: str = "Single phase"


class PaymentIn(BaseModel):
    amount: float
    method: str = "UPI"
    stage_id: Optional[str] = None
    service_id: Optional[str] = None


class ProjectCreateIn(BaseModel):
    project_code: str
    project_name: str
    site_name: str = ""
    location: str = ""
    address: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    capacity_kw: float = 0
    panel_capacity_kw: float = 0.4


class PanelBulkAddIn(BaseModel):
    project_id: str
    count: int
    manufacturer: str = "Waaree"
    model: str = "WSM-400"
    watt_rating: int = 400


class AllocateIn(BaseModel):
    project_id: str
    client_id: str
    panel_count: int


class StageUpdateIn(BaseModel):
    status: str
    notes: Optional[str] = None


class ServiceCreateIn(BaseModel):
    name: str
    description: str = ""
    base_price: float = 0


class ServiceRequestIn(BaseModel):
    service_id: str
    notes: str = ""


class ServiceRequestUpdateIn(BaseModel):
    status: str
    quoted_price: Optional[float] = None
    notes: Optional[str] = None


class TicketCreateIn(BaseModel):
    subject: str
    category: str = "GENERAL"
    description: str = ""
    priority: str = "NORMAL"


class TicketMessageIn(BaseModel):
    message: str


class AdminCreateIn(BaseModel):
    full_name: str
    username: str
    password: str
    email: Optional[str] = None
    role: str = "ADMIN"  # ADMIN or SUPER_ADMIN (primary admin creates either)


class ContactAddIn(BaseModel):
    type: str  # EMAIL / PHONE / WHATSAPP
    value: str
    label: str = ""
