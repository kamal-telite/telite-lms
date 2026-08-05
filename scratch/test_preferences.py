import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.engine import get_platform_session
from app.models.user import User
from app.models.notification_preference import NotificationPreference
from app.services.preference_resolver import PreferenceResolver
from app.services.notification_service import NotificationService
from app.repositories.notification_repo import NotificationRepository

engine = create_engine('postgresql+psycopg://postgres:postgres123@localhost:55432/telite_backend')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def run_test():
    with SessionLocal() as db:
        # Find kt_learner_2
        user = db.query(User).filter_by(username="kt_learner_2").first()
        org_id = user.org_id
        
        resolver = PreferenceResolver(db)
        
        # 1. Clean previous explicit preferences
        db.query(NotificationPreference).filter_by(user_id=user.id).delete()
        db.commit()
        
        # 2. Check defaults
        prefs = resolver.resolve_for_user(user.id, org_id, "tasks")
        assert prefs["in_app"] == True
        assert prefs["email"] == True
        
        # 3. Add override (in_app: False, email: False)
        pref = NotificationPreference(
            user_id=user.id,
            org_id=org_id,
            category="tasks",
            channel_in_app=False,
            channel_email=False
        )
        db.add(pref)
        db.commit()
        
        prefs2 = resolver.resolve_for_user(user.id, org_id, "tasks")
        assert prefs2["in_app"] == False
        assert prefs2["email"] == False
        
        # 4. Check Security is still True
        prefs_sec = resolver.resolve_for_user(user.id, org_id, "security")
        assert prefs_sec["in_app"] == True
        
        # 5. Check NotificationService
        svc = NotificationService(db)
        # Emit a task event
        svc.emit_event(
            event_name="task.assigned",
            org_id=org_id,
            context={"task_id": "999", "title": "Test Task", "assignment_id": "888"},
            recipient_id=user.id
        )
        db.commit()
        
        # Should be completely skipped because both are False
        repo = NotificationRepository(db)
        unread = repo.count_unread(user.id, org_id)
        # The unread count should not include any task.assigned for task 999
        # (Though we don't know the prior unread count, let's just make sure it didn't create it)
        notifs = repo.list_for_user(user.id, org_id)
        assert not any(n.source_id == "999" for n in notifs)
        
        # 6. Change to in_app: False, email: True
        pref.channel_email = True
        db.commit()
        
        svc.emit_event(
            event_name="task.assigned",
            org_id=org_id,
            context={"task_id": "1000", "title": "Test Task 2", "assignment_id": "889"},
            recipient_id=user.id
        )
        db.commit()
        
        notifs2 = repo.list_for_user(user.id, org_id)
        assert not any(n.source_id == "1000" for n in notifs2), "Should be hidden from in_app!"
        
        # But if we query the DB directly, it should exist!
        from app.models.notification import Notification
        raw_notif = db.query(Notification).filter_by(source_id="1000").first()
        assert raw_notif is not None
        assert '"hidden_in_app": true' in raw_notif.metadata_json
        assert '"delivery_channel": "email"' in raw_notif.metadata_json
        
        print("Backend Preference Logic Test PASSED!")
        
if __name__ == "__main__":
    run_test()
