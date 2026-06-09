from app.db.database import engine
from app.models.base import Base
# ensure all models are imported
from app.models import *

def init_db():
    Base.metadata.create_all(engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
