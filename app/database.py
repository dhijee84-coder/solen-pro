from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL (and other server DBs): pool + pre-ping for stale connections.
    engine = create_engine(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_pre_ping=True,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS ix_panels_client_id ON panels (client_id)",
    "CREATE INDEX IF NOT EXISTS ix_panels_project_id ON panels (project_id)",
    "CREATE INDEX IF NOT EXISTS ix_panels_status ON panels (status)",
    "CREATE INDEX IF NOT EXISTS ix_payments_client_id ON payments (client_id)",
    "CREATE INDEX IF NOT EXISTS ix_payments_status ON payments (status)",
    "CREATE INDEX IF NOT EXISTS ix_notifications_recipient ON notifications (recipient_user_id)",
    "CREATE INDEX IF NOT EXISTS ix_notifications_type_entity ON notifications (type, related_entity, related_entity_id)",
    "CREATE INDEX IF NOT EXISTS ix_documents_client_id ON documents (client_id)",
    "CREATE INDEX IF NOT EXISTS ix_tickets_client_id ON support_tickets (client_id)",
    "CREATE INDEX IF NOT EXISTS ix_claims_client_id ON warranty_claims (client_id)",
    "CREATE INDEX IF NOT EXISTS ix_claims_status ON warranty_claims (status)",
    "CREATE INDEX IF NOT EXISTS ix_audit_timestamp ON audit_logs (timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_audit_action ON audit_logs (action)",
    "CREATE INDEX IF NOT EXISTS ix_generation_client_date ON generation_records (client_id, date)",
    "CREATE INDEX IF NOT EXISTS ix_stages_client_id ON project_stages (client_id)",
    "CREATE INDEX IF NOT EXISTS ix_enquiries_status ON contact_enquiries (status)",
]


def ensure_indexes(bind=None):
    """Idempotent index creation for SQLite and PostgreSQL."""
    bind = bind or engine
    with bind.connect() as conn:
        for stmt in INDEX_STATEMENTS:
            try:
                conn.execute(text(stmt))
            except Exception:
                pass
        conn.commit()
