from app.db.engine import db_session
from app.repositories.publishing_repo import PublishingRepository
from app.models.user import User

db = next(db_session())
user = db.query(User).filter(User.email == 'admin@ktlearn.com').first()
repo = PublishingRepository(db)
version = repo.create_version(course_id='course-python', author_id=user.id, org_id=user.org_id)
db.commit()
print("Published version:", version.id)
