import pytest
from app.models.organization import Organization

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_health_endpoint(client, db):
    # Setup the default organization required by database seeds
    org = Organization(
        id=1,
        name="Telite Systems",
        type="company",
        domain="telite.io",
        slug="telite",
        status="active",
        plan="free"
    )
    db.add(org)
    db.commit()

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "ok"
