import json
import sys
sys.path.append('.')
from app.api.routes.management import post_category
from app.api.routes.management import CategoryPayload
from app.services.auth import TokenData
from fastapi import HTTPException

# mock db
try:
    post_category(
        body=CategoryPayload(name="Test Category", slug="test-cat", description="Test", organization_id=3),
        org_id=3,
        current_user=TokenData(id="user-kamal-pandey-239b8f", role="super_admin", org_id=3)
    )
    print("SUCCESS")
except Exception as e:
    print("FAILED", repr(e))
