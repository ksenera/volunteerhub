"""Integration tests for the PostgreSQL-backed listing API."""

import os
import sys
from pathlib import Path

import psycopg2
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend import PostgresListingRepository, create_app


TEST_DATABASE_URL = os.getenv("POSTGRES_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set POSTGRES_TEST_DATABASE_URL to run PostgreSQL integration tests.",
)


def reset_database():
    with psycopg2.connect(TEST_DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DROP TABLE IF EXISTS listing_claims;
                DROP TABLE IF EXISTS user_points;
                DROP TABLE IF EXISTS listings;
                """
            )


@pytest.fixture()
def postgres_client(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
    reset_database()
    repository = PostgresListingRepository()
    repository.init_schema()
    app = create_app(repository=repository)
    app.config.update(TESTING=True)
    yield app.test_client()
    reset_database()


def test_postgres_listing_lifecycle_and_rewards(postgres_client):
    created = postgres_client.post(
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

    assert created.status_code == 201
    listing = created.get_json()
    assert listing["id"] == 1
    assert listing["summaryReviewStatus"] == "not_generated"

    filtered = postgres_client.get("/api/listings?search=food&location=Ottawa")
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.get_json()["listings"]] == [listing["id"]]

    updated = postgres_client.put(
        f"/api/listings/{listing['id']}",
        json={**listing, "title": "Food Bank Shift Helper"},
    )
    assert updated.status_code == 200
    assert updated.get_json()["title"] == "Food Bank Shift Helper"

    summary = postgres_client.post(f"/api/listings/{listing['id']}/summary")
    assert summary.status_code == 200
    assert summary.get_json()["summaryPromptVersion"] == "listing-summary-v1"
    assert summary.get_json()["summaryReviewStatus"] == "needs_review"

    first_claim = postgres_client.post(f"/api/listings/{listing['id']}/claim")
    assert first_claim.status_code == 200
    assert first_claim.get_json()["awardedPoints"] == 50
    assert first_claim.get_json()["pointsBalance"] == 50

    duplicate_claim = postgres_client.post(f"/api/listings/{listing['id']}/claim")
    assert duplicate_claim.status_code == 200
    assert duplicate_claim.get_json()["awardedPoints"] == 0

    deleted = postgres_client.delete(f"/api/listings/{listing['id']}")
    assert deleted.status_code == 204
    assert postgres_client.get("/api/listings").get_json()["listings"] == []
