"""FIFO allocation and capacity tests (kept from the original suite)."""
import pytest

from app import models
from app.database import SessionLocal
from app.services import allocation_service
from tests.conftest import make_staff, make_project_with_panels


def test_fifo_allocation_order():
    db = SessionLocal()
    project = make_project_with_panels(db, "FIFO-1", 4)
    user = models.User(role=models.RoleName.CLIENT, full_name="C1", phone="9000000001")
    db.add(user)
    db.flush()
    profile = models.ClientProfile(user_id=user.id)
    db.add(profile)
    db.commit()

    admin = make_staff(db, models.RoleName.ADMIN, "fifo-admin")

    panels = allocation_service.allocate_panels(db, project.id, profile.id, 2, admin)
    assert [p.serial_number for p in panels] == ["FIFO-1-P001", "FIFO-1-P002"]

    user2 = models.User(role=models.RoleName.CLIENT, full_name="C2", phone="9000000002")
    db.add(user2)
    db.flush()
    profile2 = models.ClientProfile(user_id=user2.id)
    db.add(profile2)
    db.commit()

    panels2 = allocation_service.allocate_panels(db, project.id, profile2.id, 1, admin)
    assert [p.serial_number for p in panels2] == ["FIFO-1-P003"]
    db.close()


def test_capacity_full_rejects_further_allocation():
    db = SessionLocal()
    project = make_project_with_panels(db, "CAP-1", 2)
    user = models.User(role=models.RoleName.CLIENT, full_name="C1", phone="9000000003")
    db.add(user)
    db.flush()
    profile = models.ClientProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    admin = make_staff(db, models.RoleName.ADMIN, "cap-admin")

    allocation_service.allocate_panels(db, project.id, profile.id, 2, admin)
    db.refresh(project)
    assert project.status == models.ProjectStatus.FULL

    user2 = models.User(role=models.RoleName.CLIENT, full_name="C2", phone="9000000004")
    db.add(user2)
    db.flush()
    profile2 = models.ClientProfile(user_id=user2.id)
    db.add(profile2)
    db.commit()

    with pytest.raises(allocation_service.AllocationError):
        allocation_service.allocate_panels(db, project.id, profile2.id, 1, admin)
    db.close()


def test_insufficient_panels_rejected():
    db = SessionLocal()
    project = make_project_with_panels(db, "INS-1", 1)
    user = models.User(role=models.RoleName.CLIENT, full_name="C1", phone="9000000005")
    db.add(user)
    db.flush()
    profile = models.ClientProfile(user_id=user.id)
    db.add(profile)
    db.commit()
    admin = make_staff(db, models.RoleName.ADMIN, "ins-admin")

    with pytest.raises(allocation_service.AllocationError):
        allocation_service.allocate_panels(db, project.id, profile.id, 5, admin)
    db.close()
