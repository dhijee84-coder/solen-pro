"""
Seed the SuryaSetu database with development data:
  1 Primary Admin, 2 Super Admins, 5 Admins, 10 Clients,
  3 Solar Projects with 100+ panels each, sample payments, services,
  notifications, generation records, documents metadata and tickets.

Run with:  python scripts/seed.py
"""
import os
import sys
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base, engine, SessionLocal, ensure_indexes
from app import models
from app.security import hash_password
from app.permissions import ROLE_PERMISSIONS, ALL_PERMISSIONS
from app.services import project_service, allocation_service, payment_service, notification_service

FIRST_NAMES = ["Ravi", "Anita", "Suresh", "Priya", "Karthik", "Lakshmi", "Manoj", "Divya", "Arjun", "Meena"]
LAST_NAMES = ["Vishwanath", "Rao", "Kumar", "Iyer", "Gowda", "Reddy", "Nair", "Shetty", "Pillai", "Menon"]


def reset_db():
    from app.config import settings
    if settings.is_production and os.environ.get("FORCE_SEED") != "1":
        raise SystemExit(
            "Refusing to seed in production (this drops the database). "
            "Set FORCE_SEED=1 if you really intend to wipe production data."
        )
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    ensure_indexes(engine)


def seed_permissions(db):
    codes = {}
    for code in ALL_PERMISSIONS:
        p = models.Permission(code=code, description=code.replace(".", " ").replace("_", " ").title())
        db.add(p)
        db.flush()
        codes[code] = p
    for role, perms in ROLE_PERMISSIONS.items():
        for code in perms:
            db.add(models.RolePermission(role=role, permission_id=codes[code].id))
    db.commit()


def seed_staff(db):
    primary = models.User(role=models.RoleName.PRIMARY_ADMIN, full_name="System Owner",
                           username="primary", hashed_password=hash_password("ChangeMe123!"))
    db.add(primary)
    db.flush()

    super_admins = []
    for i in range(1, 3):
        u = models.User(role=models.RoleName.SUPER_ADMIN, full_name=f"Super Admin {i}",
                         username="superadmin" if i == 1 else f"superadmin{i}",
                         hashed_password=hash_password("ChangeMe123!"), created_by=primary.id)
        db.add(u)
        super_admins.append(u)
    db.flush()

    admins = []
    for i in range(1, 6):
        u = models.User(role=models.RoleName.ADMIN, full_name=f"Operations Admin {i}",
                         username="admin" if i == 1 else f"admin{i}",
                         hashed_password=hash_password("ChangeMe123!"), created_by=super_admins[0].id)
        db.add(u)
        admins.append(u)
    db.flush()
    db.commit()
    return primary, super_admins, admins


def seed_projects(db):
    projects = []
    specs = [
        ("CHN-001", "Chennai Solar Park A", "Chennai, Tamil Nadu", 13.08, 12.98),
        ("BLR-001", "Bengaluru Solar Ridge", "Bengaluru, Karnataka", 12.90, 12.79),
        ("HYD-001", "Hyderabad Solar Commons", "Hyderabad, Telangana", 13.05, 78.45),
    ]
    for code, name, loc, lat, lng in specs:
        p = models.Project(
            project_code=code, project_name=name, site_name=name, location=loc,
            address=f"{name}, {loc}", latitude=lat, longitude=lng,
            status=models.ProjectStatus.PLANNING, panel_capacity_kw=0.4,
        )
        db.add(p)
        db.flush()
        # ~120 panels per project so FIFO + capacity alerts have real headroom to demonstrate
        for i in range(120):
            serial = f"{code}-P{i+1:05d}"
            db.add(models.Panel(
                serial_number=serial, project_id=p.id, manufacturer="Waaree", model="WSM-400",
                watt_rating=400, added_sequence=i + 1, status=models.PanelStatus.AVAILABLE,
            ))
        p.total_panels = 120
        p.capacity_kw = 120 * 0.4
        p.status = models.ProjectStatus.ACTIVE
        projects.append(p)
    db.commit()
    return projects


def seed_services(db):
    names = [
        ("Panel cleaning", "Scheduled farm-side cleaning so your purchased panels keep generating.", 1500),
        ("Additional panel capacity", "Buy more modules from farm inventory.", 0),
        ("Inverter service", "Preventive maintenance on farm inverters operated by Solan.", 2500),
        ("System inspection", "Annual health check of your farm-side installation.", 2000),
        ("Extended warranty", "Extend coverage beyond the standard warranty period.", 5000),
    ]
    services = []
    for n, d, price in names:
        s = models.Service(name=n, description=d, base_price=price)
        db.add(s)
        services.append(s)
    db.commit()
    return services


def seed_demo_client(db, admins, projects, services, actor):
    """
    Dedicated DEVELOPMENT/DEMO client for visual testing of the full Client portal.
    Mobile: 9999999999  |  OTP (dev): 1234
    Clearly marked as demo/test data — do not use in production.
    """
    from datetime import datetime, timedelta

    print("Seeding DEMO Solar Customer (9999999999)...")
    user = models.User(
        role=models.RoleName.CLIENT,
        full_name="Demo Solar Customer",
        phone="9999999999",
        email="demo.client@example.com",
        is_active=True,
    )
    db.add(user)
    db.flush()

    profile = models.ClientProfile(
        user_id=user.id,
        address="Demo Solar Address, T. Nagar",
        city="Chennai",
        state="Tamil Nadu",
        pincode="600017",
        assigned_admin_id=admins[0].id if admins else None,
        kyc_status="VERIFIED",
        pan_number="ABCDE1234F",  # obviously fake/test PAN
        pan_name="DEMO SOLAR CUSTOMER",
        pan_verified_at=datetime.utcnow() - timedelta(days=20),
        aadhaar_masked="XXXX XXXX 4321",
        aadhaar_verified_at=datetime.utcnow() - timedelta(days=19),
        onboarding_stage="ACTIVE",
        admin_notes="[DEMO/TEST DATA] Seeded demo client for development UI testing. Not a real customer.",
    )
    db.add(profile)
    db.flush()

    # Electricity connection
    ec = models.ElectricityConnection(
        client_id=profile.id,
        rr_number="TNEB-DEMO-999001",
        discom="TANGEDCO",
        division="Chennai South, T. Nagar",
        service_address="Demo Solar Address, T. Nagar, Chennai 600017",
        tariff="LT Domestic",
        sanctioned_load_kw=5.0,
        avg_monthly_units=350,
        avg_monthly_bill=2485.0,
        phase="Single phase",
        proposed_kw=5.0,
        system_cost=5 * 62000,
        subsidy_estimate=78000,
        payable_amount=5 * 62000 - 78000,
    )
    db.add(ec)
    db.flush()

    # Documents (metadata only — no real files required for demo)
    for dtype, status, days_ago in [
        (models.DocumentType.PAN, models.DocumentStatus.VERIFIED, 20),
        (models.DocumentType.AADHAAR, models.DocumentStatus.VERIFIED, 19),
        (models.DocumentType.ELECTRICITY_BILL, models.DocumentStatus.VERIFIED, 18),
        (models.DocumentType.AGREEMENT, models.DocumentStatus.VERIFIED, 10),
    ]:
        doc = models.Document(
            client_id=profile.id,
            document_type=dtype,
            original_filename=f"demo_{dtype.value.lower()}.pdf",
            stored_filename=f"demo_{dtype.value.lower()}.pdf",
            file_path=f"uploads/clients/{profile.id}/{dtype.value.lower()}/demo.pdf",
            mime_type="application/pdf",
            file_size=128000,
            uploaded_by=user.id,
            uploaded_at=datetime.utcnow() - timedelta(days=days_ago),
            status=status,
            verified_by=actor.id if status == models.DocumentStatus.VERIFIED else None,
            verified_at=datetime.utcnow() - timedelta(days=days_ago - 1) if status == models.DocumentStatus.VERIFIED else None,
            notes="Demo document — test data only",
        )
        db.add(doc)

    db.commit()

    # Allocate 10 × 400W = 4 kW panels from Chennai project
    chennai = next((p for p in projects if "Chennai" in p.project_name), projects[0])
    try:
        allocation_service.allocate_panels(db, chennai.id, profile.id, 10, actor)
    except allocation_service.AllocationError as e:
        print(f"  Warning: demo panel allocation failed: {e}")
        return profile

    project_service.create_stages_for_client(db, profile.id)
    cp = db.query(models.ClientProject).filter(models.ClientProject.client_id == profile.id).first()
    if cp:
        cp.contract_total = ec.payable_amount
    db.commit()

    # Installation progress: first 5 stages COMPLETED, Installation IN_PROGRESS
    stages = (
        db.query(models.ProjectStage)
        .filter(models.ProjectStage.client_id == profile.id)
        .order_by(models.ProjectStage.stage_number)
        .all()
    )
    # Typical stage names from project_service: KYC, Site Verification, Agreement, Payment, Panel Allocation, Installation, ...
    for i, s in enumerate(stages):
        if i < 5:  # first five completed
            amount = (cp.contract_total * s.percentage / 100) if cp and s.percentage else 0
            if s.payment_required and amount > 0:
                payment_service.record_payment(db, profile, amount, "UPI", actor, stage_id=s.id)
            else:
                s.status = models.StageStatus.COMPLETED
                s.completed_at = datetime.utcnow() - timedelta(days=12 - i)
                s.payment_status = "PAID" if s.payment_required else "NOT_DUE"
        elif i == 5:  # Installation in progress
            s.status = models.StageStatus.IN_PROGRESS
            s.started_at = datetime.utcnow() - timedelta(days=3)
            s.payment_status = "NOT_DUE"
        else:
            s.status = models.StageStatus.NOT_STARTED
    db.commit()

    # Extra explicit payments for UI clarity (total ~₹40,000 paid)
    # record_payment already created some; add a couple more SUCCESS records if needed
    existing_paid = (
        db.query(models.Payment)
        .filter(models.Payment.client_id == profile.id, models.Payment.status == models.PaymentStatus.SUCCESS)
        .count()
    )
    if existing_paid < 2:
        payment_service.record_payment(db, profile, 25000, "UPI", actor)
        payment_service.record_payment(db, profile, 15000, "UPI", actor)

    # Generation history (last 60 days, realistic ~12–25 kWh/day for 4–5 kW)
    project_service.simulate_generation_history(db, chennai.id, profile.id, 4.0, days=60)

    # Service request
    cleaning = next((s for s in services if "lean" in s.name.lower()), services[0] if services else None)
    if cleaning:
        sr = models.ClientServiceRequest(
            client_id=profile.id,
            service_id=cleaning.id,
            status=models.ServiceRequestStatus.REQUESTED,
            notes="Demo request: quarterly panel cleaning",
        )
        db.add(sr)
        db.flush()
        notification_service.notify_service_request(db, sr)

    # Support ticket
    ticket = models.SupportTicket(
        client_id=profile.id,
        subject="Installation status enquiry",
        category="INSTALLATION",
        description="Could you please share the expected completion date for the ongoing installation?",
        priority="MEDIUM",
        status=models.TicketStatus.IN_PROGRESS,
        assigned_admin_id=admins[0].id if admins else None,
    )
    db.add(ticket)
    db.flush()
    notification_service.notify_client_question(db, ticket)

    # Client-facing notifications
    demo_notifs = [
        ("PANEL_ALLOCATION", "Panel allocation completed", "Your panel allocation of 10 × 400W panels has been completed."),
        ("PAYMENT", "Payment received", "Your payment of ₹25,000 was received successfully."),
        ("INSTALLATION", "Farm commissioning in progress", "Your purchased panels are being commissioned on the Solan farm — not at your house."),
        ("PAYMENT_DUE", "Next payment reminder", "Your next payment is due soon. Please check the Payments section."),
    ]
    for ntype, title, msg in demo_notifs:
        db.add(models.Notification(
            recipient_user_id=user.id,
            type=ntype,
            title=title,
            message=msg,
            priority="NORMAL",
            is_read=False,
        ))

    db.commit()
    print("  Demo client ready: Demo Solar Customer / 9999999999 / OTP 1234")
    return profile


def seed_clients(db, admins, projects, services, actor):
    clients = []
    for i in range(10):
        fn, ln = random.choice(FIRST_NAMES), random.choice(LAST_NAMES)
        name = f"{fn} {ln}"
        phone = f"98{random.randint(10000000, 99999999)}"
        user = models.User(role=models.RoleName.CLIENT, full_name=name, phone=phone,
                            email=f"{fn.lower()}.{ln.lower()}{i}@example.com")
        db.add(user)
        db.flush()
        profile = models.ClientProfile(
            user_id=user.id, city="Bengaluru", state="Karnataka",
            assigned_admin_id=random.choice(admins).id,
        )
        db.add(profile)
        db.flush()

        notification_service.notify_new_client(db, profile)

        # KYC for most clients
        if i < 9:
            profile.pan_number = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5))}{random.randint(1000,9999)}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
            profile.pan_name = name.upper()
            from datetime import datetime
            profile.pan_verified_at = datetime.utcnow()
            profile.aadhaar_masked = f"XXXX XXXX {random.randint(1000,9999)}"
            profile.aadhaar_verified_at = datetime.utcnow()
            profile.kyc_status = "VERIFIED"
            profile.onboarding_stage = "KYC_DONE"

        # Electricity connection + bill for most
        units = random.randint(220, 620)
        kw = max(1, min(10, round(units / 120)))
        if i < 8:
            ec = models.ElectricityConnection(
                client_id=profile.id, rr_number=f"BNG-{random.randint(1000000,9999999)}",
                discom="BESCOM", division="South, Jayanagar sub-division",
                service_address=f"No. {random.randint(1,99)}, Jayanagar, Bengaluru 5600{random.randint(10,99)}",
                tariff="LT-2(a) Domestic", sanctioned_load_kw=round(units/190*2)/2,
                avg_monthly_units=units, avg_monthly_bill=round(units*7.10),
                phase="Three phase" if units > 420 else "Single phase",
                proposed_kw=kw, system_cost=kw*62000,
                subsidy_estimate=min(78000, 78000 if kw>=3 else kw*30000),
            )
            ec.payable_amount = ec.system_cost - ec.subsidy_estimate
            db.add(ec)
            profile.onboarding_stage = "BILL_UPLOADED"

        db.commit()
        clients.append(profile)

    # allocate panels + create stages + payments + generation for the first 6 "active" clients
    db.commit()
    for idx, profile in enumerate(clients[:6]):
        project = projects[idx % len(projects)]
        try:
            panel_count = random.randint(3, 8)
            allocation_service.allocate_panels(db, project.id, profile.id, panel_count, actor)
        except allocation_service.AllocationError:
            continue
        project_service.create_stages_for_client(db, profile.id)
        cp = db.query(models.ClientProject).filter(models.ClientProject.client_id == profile.id).first()
        cp.contract_total = profile.electricity_connection.payable_amount if profile.electricity_connection else 200000
        db.commit()

        # simulate a couple of stages completed with payments
        stages = db.query(models.ProjectStage).filter(models.ProjectStage.client_id == profile.id).order_by(models.ProjectStage.stage_number).all()
        for s in stages[:idx % 3]:
            amount = cp.contract_total * s.percentage / 100
            payment_service.record_payment(db, profile, amount, "UPI", actor, stage_id=s.id)

        kw = profile.electricity_connection.proposed_kw if profile.electricity_connection else panel_count * 0.4
        project_service.simulate_generation_history(db, project.id, profile.id, kw, days=60)

        if idx % 4 == 0 and services:
            sr = models.ClientServiceRequest(client_id=profile.id, service_id=random.choice(services).id)
            db.add(sr)
            db.flush()
            notification_service.notify_service_request(db, sr)

        if idx % 5 == 0:
            t = models.SupportTicket(client_id=profile.id, subject="Question about my next payment date",
                                      category="BILLING", description="When is my next stage payment due?")
            db.add(t)
            db.flush()
            notification_service.notify_client_question(db, t)

        db.commit()

    # Dedicated demo client (always present, full data)
    demo = seed_demo_client(db, admins, projects, services, actor)
    clients.append(demo)

    # Warranty dates on demo client's panels
    from datetime import datetime, timedelta
    demo_panels = db.query(models.Panel).filter(models.Panel.client_id == demo.id).order_by(models.Panel.added_sequence).all()
    for i, pan in enumerate(demo_panels):
        pan.installation_date = (datetime.utcnow() - timedelta(days=400)).strftime("%Y-%m-%d")
        pan.warranty_start_date = pan.installation_date
        pan.warranty_years = 25
        pan.warranty_type = "MANUFACTURER"
        pan.warranty_provider = pan.manufacturer or "Waaree"
        if i == 0:
            # One panel expiring soon (within 60 days)
            pan.warranty_end_date = (datetime.utcnow() + timedelta(days=45)).strftime("%Y-%m-%d")
            pan.warranty_years = 1
        else:
            pan.warranty_end_date = (datetime.utcnow() + timedelta(days=365 * 24)).strftime("%Y-%m-%d")
    db.commit()

    return clients


def seed_cms(db, projects):
    """Public website content, FAQs, settings, public project flags."""
    print("Seeding website CMS, FAQs, settings...")
    settings = {
        "company_name": "Solan",
        "company_phone": "+91 44 4000 1234",
        "company_email": "hello@solan.local",
        "company_address": "Chennai, Tamil Nadu",
        "support_email": "support@solan.local",
        "support_phone": "+91 44 4000 1234",
        "hero_heading": "You buy the panels. We run the farm.",
        "hero_description": "Solan builds solar parks on open land. Clients purchase panels. We install, maintain and operate everything — and you pay for the energy those panels generate.",
        "hero_cta": "Buy panels",
        "about_mission": "Let people own solar capacity without rooftop construction. Fair panel sales, farm-side operations, usage-based energy billing.",
        "about_vision": "A trusted farm operator: our land, your panels, our maintenance, your generation.",
        "about_body": "Solan develops solar farms on empty land. Clients buy panels at those farms. We install, maintain and operate the plant. You never host equipment on your house — you buy capacity, then pay for the energy those panels generate.",
        "footer_text": "We own the land and the farm. You own the panels. We maintain everything and bill energy on usage.",
        "seo_title": "Solan — Buy farm panels. Pay for the energy you use.",
        "seo_description": "Company-owned solar farms on open land. Clients buy panels. Solan maintains the plant and bills energy on usage. No rooftop installation.",
        "section_projects": "on",
        "section_services": "on",
        "section_faq": "on",
        "section_contact": "on",
        "warranty_expiring_days": "90",
        "primary_color": "#f9c80e",
        "accent_color": "#f97316",
    }
    for k, v in settings.items():
        db.add(models.SystemSetting(key=k, value=v))
        db.add(models.WebsiteContent(key=k, value=v))

    faqs = [
        ("What is Solan?", "Solan builds solar farms on open land. You buy panels at those farms. We install, maintain and operate everything. You pay for the energy those panels generate. We do not install on rooftops or houses.", "GENERAL"),
        ("Do you install panels on my house?", "No. Solan never mounts equipment on homes or rooftops. All panels stay on company-operated farms.", "GENERAL"),
        ("How do I register?", "Use Client Login, enter your 10-digit mobile number, and verify with the OTP. Development OTP is always 1234.", "ONBOARDING"),
        ("How are panels allocated?", "Available farm panels are sold first-in, first-out from the selected site inventory.", "ALLOCATION"),
        ("How is energy billed?", "Generation from your purchased panels is metered. You pay for the energy those panels produce — usage, not a rooftop plant.", "BILLING"),
        ("Who maintains the panels?", "Solan. Cleaning, repairs, warranty claims and plant operations stay our responsibility after you buy the panels.", "MAINTENANCE"),
        ("How do warranty claims work?", "Open My Panels, select a panel, and submit a warranty claim. Staff review and update the claim status.", "WARRANTY"),
        ("How do I contact support?", "Registered clients should open a support ticket in the portal. Visitors can use the Contact page.", "SUPPORT"),
    ]
    for i, (q, a, cat) in enumerate(faqs):
        db.add(models.FAQ(question=q, answer=a, category=cat, sort_order=i, is_active=True))

    # Mark Chennai project public
    for p in projects:
        if "Chennai" in p.project_name:
            p.is_public = True
            p.public_description = "Active Solan farm in Chennai. Buy panels on our open-land site; we operate and maintain them."
        if "Bengaluru" in p.project_name:
            p.is_public = True
            p.public_description = "Bengaluru farm with capacity for new panel purchases. No rooftop work — farm-side only."

    db.add(models.Announcement(
        title="Welcome to Solan",
        message="Buy farm panels, track generation and pay for energy on usage. Demo client is on the login page.",
        cta_text="Client Login",
        cta_url="/login",
        is_published=True,
    ))
    db.commit()


def main():
    print("Resetting database...")
    reset_db()
    db = SessionLocal()
    try:
        print("Seeding permissions...")
        seed_permissions(db)
        print("Seeding staff accounts...")
        primary, super_admins, admins = seed_staff(db)
        print("Seeding projects and panel inventory...")
        projects = seed_projects(db)
        print("Seeding service catalog...")
        services = seed_services(db)
        print("Seeding clients, allocations, payments, generation...")
        seed_clients(db, admins, projects, services, primary)
        seed_cms(db, projects)
        print("\nSeed complete.\n")
        print("Login credentials (development only):")
        print("  Primary Admin  -> username: primary       password: ChangeMe123!")
        print("  Super Admin    -> username: superadmin    password: ChangeMe123!")
        print("  Admin          -> username: admin          password: ChangeMe123!")
        print("\n  DEMO CLIENT (for Client portal testing):")
        print("    Name   : Demo Solar Customer")
        print("    Mobile : 9999999999   (enter as 9999999999)")
        print("    OTP    : 1234         (development OTP)")
        print("    Email  : demo.client@example.com")
        print("\nClients sign in via mobile OTP at /login — the dev OTP is always 1234.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
