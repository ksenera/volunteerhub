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


def test_create_listing_validation(client):
    response = client.post("/api/listings", json={"title": "", "organization": ""})

    assert response.status_code == 400
    assert response.get_json()["errors"] == {
        "title": "This field is required.",
        "organization": "This field is required.",
        "commitment": "This field is required.",
        "location": "This field is required.",
    }


def test_listing_validation_rejects_negative_distance(client):
    response = client.post(
        "/api/listings",
        json={
            "title": "Park Cleanup",
            "organization": "Green Ottawa",
            "commitment": "Flexible",
            "location": "Ottawa",
            "distanceMinutes": -5,
        },
    )

    assert response.status_code == 400
    assert response.get_json()["errors"] == {
        "distanceMinutes": "Distance must be zero or more minutes."
    }


def test_listing_validation_rejects_non_numeric_distance(client):
    response = client.post(
        "/api/listings",
        json={
            "title": "Park Cleanup",
            "organization": "Green Ottawa",
            "commitment": "Flexible",
            "location": "Ottawa",
            "distanceMinutes": "nearby",
        },
    )

    assert response.status_code == 400
    assert response.get_json()["errors"] == {
        "distanceMinutes": "Distance must be a number of minutes."
    }


def test_update_listing_validation_errors(client):
    response = client.put("/api/listings/1", json={"title": "", "organization": ""})

    assert response.status_code == 400
    assert response.get_json()["errors"]["title"] == "This field is required."
    assert response.get_json()["errors"]["commitment"] == "This field is required."


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


def test_missing_listing_routes_return_404(client):
    update = client.put(
        "/api/listings/999",
        json={
            "title": "Missing Listing",
            "organization": "No Org",
            "commitment": "Flexible",
            "location": "Remote",
        },
    )
    summary = client.post("/api/listings/999/summary")
    claim = client.post("/api/listings/999/claim")

    assert update.status_code == 404
    assert summary.status_code == 404
    assert claim.status_code == 404


def test_claim_points_and_redeem_rewards(client):
    rewards = client.get("/api/rewards")
    assert rewards.status_code == 200
    assert rewards.get_json()["pointsBalance"] == 0

    claimed = client.post("/api/listings/2/claim")
    assert claimed.status_code == 200
    claim_data = claimed.get_json()
    assert claim_data["awardedPoints"] == 500
    assert claim_data["pointsBalance"] == 500
    assert claim_data["listing"]["claimed"] is True

    duplicate = client.post("/api/listings/2/claim")
    assert duplicate.status_code == 200
    assert duplicate.get_json()["awardedPoints"] == 0

    too_expensive = client.post("/api/rewards/redeem", json={"rewardId": "amazon"})
    assert too_expensive.status_code == 400
    assert too_expensive.get_json()["error"] == "Not enough points to redeem this reward."

    client.post(
        "/api/listings",
        json={
            "title": "Mentor Team Lead",
            "organization": "Youth Mentors",
            "commitment": "Ongoing",
            "location": "Ottawa",
        },
    )
    client.post(
        "/api/listings",
        json={
            "title": "Program Support Lead",
            "organization": "Community Lab",
            "commitment": "Ongoing",
            "location": "Remote",
        },
    )
    client.post("/api/listings/3/claim")
    client.post("/api/listings/4/claim")
    redeemed = client.post("/api/rewards/redeem", json={"rewardId": "amazon"})
    assert redeemed.status_code == 200
    assert redeemed.get_json()["redeemedReward"]["id"] == "amazon"
    assert redeemed.get_json()["pointsBalance"] == 1500


def test_unknown_reward_returns_404(client):
    response = client.post("/api/rewards/redeem", json={"rewardId": "not-real"})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Reward not found."


def test_missing_reward_id_returns_404(client):
    response = client.post("/api/rewards/redeem", json={})

    assert response.status_code == 404
    assert response.get_json()["error"] == "Reward not found."
