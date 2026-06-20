import pytest
from sqlalchemy.orm import Session
from app.services.user_provisioning import UserProvisioningService, ProvisioningError
from app.models.user import User
from app.models.organization import Organization
from app.models.invitation import OrgInvitation
from datetime import datetime, timedelta

@pytest.fixture
def test_orgs(db_session: Session):
    org1 = Organization(id=1, name="Tenant A", type="college", domain="tenant-a.com", slug="tenant-a", plan="pro")
    org2 = Organization(id=2, name="Tenant B", type="company", domain="tenant-b.com", slug="tenant-b", plan="free")
    db_session.add_all([org1, org2])
    
    actor = User(
        id="user-admin1",
        username="admin1",
        email="admin@tenanta.com",
        full_name="Admin",
        role="org_admin",
        password_hash="hash",
        avatar_initials="AD",
        gradient_start="0",
        gradient_end="0",
        is_active=True,
        is_platform_admin=False,
        status="active",
        org_id=1,
        organization_id=1,
    )
    db_session.add(actor)
    db_session.commit()
    return org1, org2, actor

def test_tenant_isolation(db_session: Session, test_orgs):
    org1, org2, actor = test_orgs
    svc = UserProvisioningService(db_session)
    
    # 1. Invite a user to org 1
    inv1 = svc.invite_learner(
        email="learner@test.com",
        username="learner1",
        full_name="Learner One",
        role="learner",
        org_id=1,
        actor=actor
    )
    db_session.commit()
    
    # 2. Try to invite the same email to org 2
    with pytest.raises(ProvisioningError, match="Email already belongs to another organization"):
        svc.invite_learner(
            email="learner@test.com",
            username="learner2",
            full_name="Learner Two",
            role="learner",
            org_id=2,
            actor=actor
        )

def test_duplicate_username(db_session: Session, test_orgs):
    org1, org2, actor = test_orgs
    svc = UserProvisioningService(db_session)
    
    svc.invite_learner(
        email="user1@test.com",
        username="same_user",
        full_name="User 1",
        role="learner",
        org_id=1,
        actor=actor
    )
    db_session.commit()
    
    with pytest.raises(ProvisioningError, match="Username is already taken globally"):
        svc.invite_learner(
            email="user2@test.com",
            username="same_user",
            full_name="User 2",
            role="learner",
            org_id=1,
            actor=actor
        )

def test_duplicate_email(db_session: Session, test_orgs):
    org1, org2, actor = test_orgs
    svc = UserProvisioningService(db_session)
    
    svc.invite_learner(
        email="duplicate@test.com",
        username="user1",
        full_name="User 1",
        role="learner",
        org_id=1,
        actor=actor
    )
    db_session.commit()
    
    with pytest.raises(ProvisioningError, match="Email is already invited to this organization"):
        svc.invite_learner(
            email="duplicate@test.com",
            username="user2",
            full_name="User 2",
            role="learner",
            org_id=1,
            actor=actor
        )

def test_expired_invitation(db_session: Session, test_orgs):
    org1, org2, actor = test_orgs
    svc = UserProvisioningService(db_session)
    
    inv = svc.invite_learner(
        email="expired@test.com",
        username="expired_user",
        full_name="Expired",
        role="learner",
        org_id=1,
        actor=actor
    )
    
    # Manually expire
    inv.expires_at = (datetime.utcnow() - timedelta(days=1)).isoformat()
    db_session.commit()
    
    with pytest.raises(ProvisioningError, match="Invitation has expired"):
        svc.accept_invitation(inv.token, "newpassword123")

def test_unaccepted_invitation(db_session: Session, test_orgs):
    org1, org2, actor = test_orgs
    svc = UserProvisioningService(db_session)
    
    inv = svc.invite_learner(
        email="pending@test.com",
        username="pending_user",
        full_name="Pending",
        role="learner",
        org_id=1,
        actor=actor
    )
    db_session.commit()
    
    assert inv.delivery_status == "pending"

def test_accepted_invitation(db_session: Session, test_orgs):
    org1, org2, actor = test_orgs
    svc = UserProvisioningService(db_session)
    
    inv = svc.invite_learner(
        email="accept@test.com",
        username="accept_user",
        full_name="Accept",
        role="learner",
        org_id=1,
        actor=actor
    )
    db_session.commit()
    
    user = svc.accept_invitation(inv.token, "newpassword123")
    db_session.commit()
    
    assert inv.delivery_status == "accepted"
    assert user.email == "accept@test.com"
    assert user.username == "accept_user"
    assert user.invited_via == "admin_invitation"
