import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "telite-backend"))

from app.db.engine import get_engine
from app.models.learning_path import LearningPath, LearningPathCourse

print("Creating learning paths tables...")
engine = get_engine()
LearningPath.__table__.create(engine, checkfirst=True)
LearningPathCourse.__table__.create(engine, checkfirst=True)
print("Done.")
