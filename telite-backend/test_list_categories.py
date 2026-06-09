import sys
sys.path.append('.')
from app.services.store import list_categories

print(list_categories(org_id=3))
