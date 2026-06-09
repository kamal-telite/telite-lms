import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.engine import get_engine
from app.models.base import Base
from app.models.media_asset import MediaAsset

def recreate_media_assets():
    engine = get_engine()
    print("Dropping media_assets table...")
    MediaAsset.__table__.drop(engine, checkfirst=True)
    print("Creating media_assets table...")
    MediaAsset.__table__.create(engine)
    print("Done!")

if __name__ == "__main__":
    recreate_media_assets()
