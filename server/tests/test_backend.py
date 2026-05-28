import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import MemoryListingRepository, create_app


@pytest.fixture()
def client():
    app = create_app(repository=MemoryListingRepository())
    app.config.update(TESTING=True)
    return app.test_client()


def test_health(client):
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_create_and_filter_listing(client):
    response = client.post(
        "/api/listings",
        json={
            "title": "Food Bank Helper",
            "organization": "Ottawa Food Bank",
            "organizationTypes": "Community Support",
            "volunteerTypes": "Food Security",
            "commitment": "Flexible",
            "location": "Ottawa",
            "applicationDeadline": "May 30, 2026",
            "website": "https://example.com",
            "distanceMinutes": 15,
        },
    )

    assert response.status_code == 201
    created = response.get_json()
    assert created["title"] == "Food Bank Helper"

    filtered = client.get("/api/listings?search=food&location=Ottawa")
    listings = filtered.get_json()["listings"]
    assert filtered.status_code == 200
    assert len(listings) == 1
    assert listings[0]["organization"] == "Ottawa Food Bank"


def test_update_delete_and_summary(client):
    created = client.post(
        "/api/listings",
        json={
            "title": "Library Tutor",
            "organization": "City Library",
            "commitment": "Short term",
            "location": "Remote",
        },
    ).get_json()

    updated = client.put(
        f"/api/listings/{created['id']}",
        json={
            **created,
            "title": "Library Reading Tutor",
        },
    )
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Library Reading Tutor"

    summary = client.post(f"/api/listings/{created['id']}/summary")
    assert summary.status_code == 200
    assert summary.get_json()["summaryReviewStatus"] == "needs_review"

    deleted = client.delete(f"/api/listings/{created['id']}")
    assert deleted.status_code == 204
    assert client.delete(f"/api/listings/{created['id']}").status_code == 404
