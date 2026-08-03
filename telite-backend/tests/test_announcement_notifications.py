"""Test announcement notification creation."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType
from app.models.announcement import Announcement, AnnouncementAudience
from app.models.user import User
from app.repositories.notification_repo import NotificationRepository
from app.repositories.announcement_repo import AnnouncementRepository
from app.repositories.user_repo import UserRepository


@pytest.fixture
def test_org(db_session: Session):
    """Create a test organization."""
    from app.models.organization import Organization
    org = Organization(
        name="Test Org",
        status="active",
    )
    db_session.add(org)
    db_session.flush()
    return org


@pytest.fixture
def admin_user(db_session: Session, test_org):
    """Create an admin user."""
    user = User(
        id="admin1",
        email="admin@test.com",
        full_name="Admin User",
        role="admin",
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def learner_user(db_session: Session, test_org):
    """Create a learner user."""
    user = User(
        id="learner1",
        email="learner@test.com",
        full_name="Learner User",
        role="learner",
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def category_admin_user(db_session: Session, test_org):
    """Create a category admin user."""
    user = User(
        id="catadmin1",
        email="catadmin@test.com",
        full_name="Category Admin",
        role="category_admin",
        category_scope="tech",
        org_id=test_org.id,
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_announcement_published_creates_notifications_for_all_users(
    db_session: Session, test_org, admin_user, learner_user, category_admin_user
):
    """Test that publishing an announcement creates notifications for all users when audience is 'all'."""
    # Create announcement with 'all' audience
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="System Maintenance",
        body="The system will be down for maintenance on Sunday.",
        created_by=admin_user.id,
        audience_type="all",
        audience_value=None,
        status="published",
    )
    db_session.commit()
    
    # Verify notifications were created for all active users
    notification_repo = NotificationRepository(db_session)
    
    # Check admin notification
    admin_notifications = notification_repo.list_for_user(
        user_id=admin_user.id,
        org_id=test_org.id,
    )
    assert len(admin_notifications) > 0
    admin_announcement_notif = [
        n for n in admin_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(admin_announcement_notif) == 1
    assert admin_announcement_notif[0].title == "New Announcement: System Maintenance"
    
    # Check learner notification
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    learner_announcement_notif = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(learner_announcement_notif) == 1
    
    # Check category admin notification
    cat_admin_notifications = notification_repo.list_for_user(
        user_id=category_admin_user.id,
        org_id=test_org.id,
    )
    cat_admin_announcement_notif = [
        n for n in cat_admin_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(cat_admin_announcement_notif) == 1


def test_announcement_published_creates_notifications_for_role(
    db_session: Session, test_org, admin_user, learner_user, category_admin_user
):
    """Test that publishing an announcement creates notifications only for targeted role."""
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Learner Update",
        body="New courses available for learners.",
        created_by=admin_user.id,
        audience_type="role",
        audience_value="learner",
        status="published",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    
    # Check learner notification (should exist)
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    learner_announcement_notif = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(learner_announcement_notif) == 1
    
    # Check admin notification (should NOT exist for this role-targeted announcement)
    admin_notifications = notification_repo.list_for_user(
        user_id=admin_user.id,
        org_id=test_org.id,
    )
    admin_announcement_notif = [
        n for n in admin_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(admin_announcement_notif) == 0


def test_announcement_published_creates_notifications_for_category(
    db_session: Session, test_org, admin_user, learner_user, category_admin_user
):
    """Test that publishing an announcement creates notifications only for targeted category."""
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Tech Category Update",
        body="New tech courses available.",
        created_by=admin_user.id,
        audience_type="category",
        audience_value="tech",
        status="published",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    
    # Check category admin notification (should exist)
    cat_admin_notifications = notification_repo.list_for_user(
        user_id=category_admin_user.id,
        org_id=test_org.id,
    )
    cat_admin_announcement_notif = [
        n for n in cat_admin_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(cat_admin_announcement_notif) == 1
    
    # Check learner notification (should NOT exist - learner doesn't have category scope)
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    learner_announcement_notif = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(learner_announcement_notif) == 0


def test_announcement_published_creates_notifications_for_specific_user(
    db_session: Session, test_org, admin_user, learner_user, category_admin_user
):
    """Test that publishing an announcement creates notification only for targeted user."""
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Personal Message",
        body="This is a personal announcement for you.",
        created_by=admin_user.id,
        audience_type="user",
        audience_value=learner_user.id,
        status="published",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    
    # Check learner notification (should exist)
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    learner_announcement_notif = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(learner_announcement_notif) == 1
    
    # Check admin notification (should NOT exist)
    admin_notifications = notification_repo.list_for_user(
        user_id=admin_user.id,
        org_id=test_org.id,
    )
    admin_announcement_notif = [
        n for n in admin_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(admin_announcement_notif) == 0


def test_draft_announcement_does_not_create_notifications(
    db_session: Session, test_org, admin_user, learner_user
):
    """Test that creating a draft announcement does not create notifications."""
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Draft Announcement",
        body="This is a draft.",
        created_by=admin_user.id,
        audience_type="all",
        audience_value=None,
        status="draft",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    
    # Check that no notifications were created
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    announcement_notifs = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(announcement_notifs) == 0


def test_updating_draft_to_published_creates_notifications(
    db_session: Session, test_org, admin_user, learner_user
):
    """Test that updating a draft to published creates notifications."""
    repo = AnnouncementRepository(db_session)
    
    # Create draft
    announcement = repo.create(
        org_id=test_org.id,
        title="Updated Announcement",
        body="This was a draft, now published.",
        created_by=admin_user.id,
        audience_type="all",
        audience_value=None,
        status="draft",
    )
    db_session.commit()
    
    # Verify no notifications yet
    notification_repo = NotificationRepository(db_session)
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    announcement_notifs = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(announcement_notifs) == 0
    
    # Update to published
    announcement = repo.update(
        announcement_id=announcement.id,
        org_id=test_org.id,
        status="published",
    )
    db_session.commit()
    
    # Verify notifications were created
    learner_notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    announcement_notifs = [
        n for n in learner_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(announcement_notifs) == 1


def test_notification_metadata_includes_correct_route(
    db_session: Session, test_org, admin_user, learner_user
):
    """Test that announcement notifications include correct navigation route."""
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Route Test",
        body="Testing notification route.",
        created_by=admin_user.id,
        audience_type="user",
        audience_value=learner_user.id,
        status="published",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    
    announcement_notif = [
        n for n in notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(announcement_notif) == 1
    
    metadata = announcement_notif[0].metadata_payload()
    assert metadata.get("route") == "/learner/announcements"
    assert metadata.get("route_name") == "learner_announcements"
    assert metadata.get("announcement_id") == announcement.id


def test_notification_body_truncation(
    db_session: Session, test_org, admin_user, learner_user
):
    """Test that long announcement bodies are truncated in notifications."""
    long_body = "This is a very long announcement body. " * 20  # Over 200 chars
    
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Long Body Test",
        body=long_body,
        created_by=admin_user.id,
        audience_type="user",
        audience_value=learner_user.id,
        status="published",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    notifications = notification_repo.list_for_user(
        user_id=learner_user.id,
        org_id=test_org.id,
    )
    
    announcement_notif = [
        n for n in notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(announcement_notif) == 1
    
    # Body should be truncated to 200 chars + "..."
    assert len(announcement_notif[0].body) <= 203
    assert announcement_notif[0].body.endswith("...")


def test_inactive_users_do_not_receive_notifications(
    db_session: Session, test_org, admin_user
):
    """Test that inactive users do not receive announcement notifications."""
    # Create inactive user
    inactive_user = User(
        id="inactive1",
        email="inactive@test.com",
        full_name="Inactive User",
        role="learner",
        org_id=test_org.id,
        is_active=False,
    )
    db_session.add(inactive_user)
    db_session.flush()
    
    # Create announcement for all
    repo = AnnouncementRepository(db_session)
    announcement = repo.create(
        org_id=test_org.id,
        title="Test",
        body="Test body",
        created_by=admin_user.id,
        audience_type="all",
        audience_value=None,
        status="published",
    )
    db_session.commit()
    
    notification_repo = NotificationRepository(db_session)
    
    # Inactive user should not receive notification
    inactive_notifications = notification_repo.list_for_user(
        user_id=inactive_user.id,
        org_id=test_org.id,
    )
    announcement_notifs = [
        n for n in inactive_notifications 
        if n.type == NotificationType.ANNOUNCEMENT_PUBLISHED.value
        and n.source_id == str(announcement.id)
    ]
    assert len(announcement_notifs) == 0
