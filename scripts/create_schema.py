import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '../telite-backend/.env'))

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../telite-backend')))

from app.db.engine import get_engine
from app.models.base import Base
from app.models import *
import app.models.certificate

def create_schema():
    engine = get_engine()
    Base.metadata.create_all(engine)
    print("Schema created successfully!")

if __name__ == "__main__":
    create_schema()
