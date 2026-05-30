import os
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from psycopg2.extras import RealDictCursor

load_dotenv()

SUMMARY_PROMPT_VERSION = "listing-summary-v1"
DEMO_USER_ID = "demo-user"
REWARDS = [
    {"id": "amazon", "name": "Amazon Gift Card", "pointsCost": 3000},
    {"id": "starbucks", "name": "Starbucks Gift Card", "pointsCost": 5000},
    {"id": "visa", "name": "Visa Gift Card", "pointsCost": 10000},
]


def points_for_commitment(commitment):
    if commitment.startswith("Flexible"):
        return 50
    if commitment.startswith("Short term"):
        return 100
    if commitment.startswith("Long term"):
        return 500
    if commitment.startswith("Ongoing"):
        return 2000
    return 10


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def database_url():
    return os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/volottdb",
    )


def connect():
    return psycopg2.connect(database_url())


def row_to_listing(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "organization": row["organization"],
        "organizationTypes": row["organization_types"],
        "volunteerTypes": row["volunteer_types"],
        "commitment": row["commitment"],
        "location": row["location"],
        "applicationDeadline": row["application_deadline"],
        "website": row["website"],
        "distanceMinutes": row["distance_minutes"],
        "summary": row.get("summary"),
        "summaryPromptVersion": row.get("summary_prompt_version"),
        "summaryReviewStatus": row.get("summary_review_status", "not_generated"),
        "pointsValue": points_for_commitment(row["commitment"]),
        "claimed": bool(row.get("claimed", False)),
        "createdAt": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updatedAt": row.get("updated_at").isoformat() if row.get("updated_at") else None,
    }


def rewards_state(points_balance):
    return {
        "pointsBalance": points_balance,
        "rewards": [
            {
                **reward,
                "canRedeem": points_balance >= reward["pointsCost"],
            }
            for reward in REWARDS
        ],
    }


def validate_listing(payload, partial=False):
    errors = {}
    required = ["title", "organization", "commitment", "location"]

    for field in required:
        if not partial and not str(payload.get(field, "")).strip():
            errors[field] = "This field is required."

    distance = payload.get("distanceMinutes")
    if distance not in (None, ""):
        try:
            distance = int(distance)
            if distance < 0:
                errors["distanceMinutes"] = "Distance must be zero or more minutes."
        except (TypeError, ValueError):
            errors["distanceMinutes"] = "Distance must be a number of minutes."

    if errors:
        return None, errors

    return {
        "title": str(payload.get("title", "")).strip(),
        "organization": str(payload.get("organization", "")).strip(),
        "organizationTypes": str(payload.get("organizationTypes", "")).strip(),
        "volunteerTypes": str(payload.get("volunteerTypes", "")).strip(),
        "commitment": str(payload.get("commitment", "")).strip(),
        "location": str(payload.get("location", "")).strip(),
        "applicationDeadline": str(payload.get("applicationDeadline", "")).strip(),
        "website": str(payload.get("website", "")).strip(),
        "distanceMinutes": int(distance) if distance not in (None, "") else 0,
    }, {}


class PostgresListingRepository:
    def init_schema(self):
        sql = """
        CREATE TABLE IF NOT EXISTS listings (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            organization TEXT NOT NULL,
            organization_types TEXT NOT NULL DEFAULT '',
            volunteer_types TEXT NOT NULL DEFAULT '',
            commitment TEXT NOT NULL,
            location TEXT NOT NULL,
            application_deadline TEXT NOT NULL DEFAULT '',
            website TEXT NOT NULL DEFAULT '',
            distance_minutes INTEGER NOT NULL DEFAULT 0,
            summary TEXT,
            summary_prompt_version TEXT,
            summary_review_status TEXT NOT NULL DEFAULT 'not_generated',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS user_points (
            user_id TEXT PRIMARY KEY,
            points_balance INTEGER NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        );

        CREATE TABLE IF NOT EXISTS listing_claims (
            user_id TEXT NOT NULL,
            listing_id INTEGER NOT NULL REFERENCES listings(id) ON DELETE CASCADE,
            points_awarded INTEGER NOT NULL,
            claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (user_id, listing_id)
        );
        """
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)

    def list(self, search="", location="", commitment=""):
        clauses = []
        values = []
        if search:
            clauses.append("(title ILIKE %s OR organization ILIKE %s OR volunteer_types ILIKE %s)")
            term = f"%{search}%"
            values.extend([term, term, term])
        if location:
            clauses.append("location = %s")
            values.append(location)
        if commitment:
            clauses.append("commitment = %s")
            values.append(commitment)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"""
        SELECT listings.*,
            EXISTS (
                SELECT 1
                FROM listing_claims
                WHERE listing_claims.listing_id = listings.id
                  AND listing_claims.user_id = %s
            ) AS claimed
        FROM listings
        {where}
        ORDER BY created_at DESC, id DESC;
        """
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, [DEMO_USER_ID, *values])
                return [row_to_listing(row) for row in cur.fetchall()]

    def get(self, listing_id):
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT listings.*,
                        EXISTS (
                            SELECT 1
                            FROM listing_claims
                            WHERE listing_claims.listing_id = listings.id
                              AND listing_claims.user_id = %s
                        ) AS claimed
                    FROM listings
                    WHERE listings.id = %s;
                    """,
                    (DEMO_USER_ID, listing_id),
                )
                row = cur.fetchone()
                return row_to_listing(row) if row else None

    def create(self, listing):
        sql = """
        INSERT INTO listings (
            title, organization, organization_types, volunteer_types, commitment,
            location, application_deadline, website, distance_minutes
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *;
        """
        values = (
            listing["title"],
            listing["organization"],
            listing["organizationTypes"],
            listing["volunteerTypes"],
            listing["commitment"],
            listing["location"],
            listing["applicationDeadline"],
            listing["website"],
            listing["distanceMinutes"],
        )
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                return row_to_listing(cur.fetchone())

    def update(self, listing_id, listing):
        sql = """
        UPDATE listings
        SET title = %s,
            organization = %s,
            organization_types = %s,
            volunteer_types = %s,
            commitment = %s,
            location = %s,
            application_deadline = %s,
            website = %s,
            distance_minutes = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING *;
        """
        values = (
            listing["title"],
            listing["organization"],
            listing["organizationTypes"],
            listing["volunteerTypes"],
            listing["commitment"],
            listing["location"],
            listing["applicationDeadline"],
            listing["website"],
            listing["distanceMinutes"],
            listing_id,
        )
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                row = cur.fetchone()
                return row_to_listing(row) if row else None

    def get_points_balance(self):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_points (user_id, points_balance)
                    VALUES (%s, 0)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    (DEMO_USER_ID,),
                )
                cur.execute(
                    "SELECT points_balance FROM user_points WHERE user_id = %s;",
                    (DEMO_USER_ID,),
                )
                return cur.fetchone()[0]

    def claim_listing(self, listing_id):
        listing = self.get(listing_id)
        if not listing:
            return None

        points = listing["pointsValue"]
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_points (user_id, points_balance)
                    VALUES (%s, 0)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    (DEMO_USER_ID,),
                )
                cur.execute(
                    """
                    INSERT INTO listing_claims (user_id, listing_id, points_awarded)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, listing_id) DO NOTHING;
                    """,
                    (DEMO_USER_ID, listing_id, points),
                )
                already_claimed = cur.rowcount == 0
                if not already_claimed:
                    cur.execute(
                        """
                        UPDATE user_points
                        SET points_balance = points_balance + %s,
                            updated_at = NOW()
                        WHERE user_id = %s;
                        """,
                        (points, DEMO_USER_ID),
                    )
                cur.execute(
                    "SELECT points_balance FROM user_points WHERE user_id = %s;",
                    (DEMO_USER_ID,),
                )
                points_balance = cur.fetchone()[0]

        updated_listing = self.get(listing_id)
        return {
            "listing": updated_listing,
            "pointsBalance": points_balance,
            "awardedPoints": 0 if already_claimed else points,
            "alreadyClaimed": already_claimed,
        }

    def redeem_reward(self, reward_id):
        reward = next((item for item in REWARDS if item["id"] == reward_id), None)
        if not reward:
            return None

        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO user_points (user_id, points_balance)
                    VALUES (%s, 0)
                    ON CONFLICT (user_id) DO NOTHING;
                    """,
                    (DEMO_USER_ID,),
                )
                cur.execute(
                    "SELECT points_balance FROM user_points WHERE user_id = %s FOR UPDATE;",
                    (DEMO_USER_ID,),
                )
                points_balance = cur.fetchone()[0]
                if points_balance < reward["pointsCost"]:
                    return {
                        "error": "Not enough points to redeem this reward.",
                        **rewards_state(points_balance),
                    }
                points_balance -= reward["pointsCost"]
                cur.execute(
                    """
                    UPDATE user_points
                    SET points_balance = %s,
                        updated_at = NOW()
                    WHERE user_id = %s;
                    """,
                    (points_balance, DEMO_USER_ID),
                )
                return {
                    "redeemedReward": reward,
                    **rewards_state(points_balance),
                }

    def delete(self, listing_id):
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM listings WHERE id = %s;", (listing_id,))
                return cur.rowcount > 0

    def save_summary(self, listing_id, summary, status="needs_review"):
        sql = """
        UPDATE listings
        SET summary = %s,
            summary_prompt_version = %s,
            summary_review_status = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING *;
        """
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (summary, SUMMARY_PROMPT_VERSION, status, listing_id))
                row = cur.fetchone()
                return row_to_listing(row) if row else None


class MemoryListingRepository:
    def __init__(self):
        self.next_id = 3
        self.points_balance = 0
        self.claimed_listing_ids = set()
        self.listings = [
            {
                "id": 1,
                "title": "Web Developer and Research Assistant",
                "organization": "Spill The Code",
                "organizationTypes": "Education, Children, Youth and Family",
                "volunteerTypes": "Technology, Communications and Marketing",
                "commitment": "Short term",
                "location": "Ottawa - West",
                "applicationDeadline": "April 30, 2025",
                "website": "https://example.com",
                "distanceMinutes": 20,
                "summary": None,
                "summaryPromptVersion": None,
                "summaryReviewStatus": "not_generated",
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            },
            {
                "id": 2,
                "title": "Community Event Organizer",
                "organization": "Local Initiatives",
                "organizationTypes": "Community Development",
                "volunteerTypes": "Event Planning, Outreach",
                "commitment": "Long term",
                "location": "Remote",
                "applicationDeadline": "June 1, 2025",
                "website": "https://example.org",
                "distanceMinutes": 0,
                "summary": None,
                "summaryPromptVersion": None,
                "summaryReviewStatus": "not_generated",
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            },
        ]

    def init_schema(self):
        return None

    def with_rewards(self, listing):
        if not listing:
            return None
        return {
            **listing,
            "pointsValue": points_for_commitment(listing["commitment"]),
            "claimed": listing["id"] in self.claimed_listing_ids,
        }

    def list(self, search="", location="", commitment=""):
        results = self.listings
        if search:
            term = search.lower()
            results = [
                listing
                for listing in results
                if term in listing["title"].lower()
                or term in listing["organization"].lower()
                or term in listing["volunteerTypes"].lower()
            ]
        if location:
            results = [listing for listing in results if listing["location"] == location]
        if commitment:
            results = [listing for listing in results if listing["commitment"] == commitment]
        return [self.with_rewards(listing) for listing in reversed(results)]

    def get(self, listing_id):
        return self.with_rewards(
            next((listing for listing in self.listings if listing["id"] == listing_id), None)
        )

    def create(self, listing):
        created = {
            **listing,
            "id": self.next_id,
            "summary": None,
            "summaryPromptVersion": None,
            "summaryReviewStatus": "not_generated",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
        }
        self.next_id += 1
        self.listings.append(created)
        return self.with_rewards(created)

    def update(self, listing_id, listing):
        existing = self.get(listing_id)
        if not existing:
            return None
        existing.update({**listing, "updatedAt": now_iso()})
        return self.with_rewards(existing)

    def delete(self, listing_id):
        existing = next((listing for listing in self.listings if listing["id"] == listing_id), None)
        if not existing:
            return False
        self.listings.remove(existing)
        self.claimed_listing_ids.discard(listing_id)
        return True

    def save_summary(self, listing_id, summary, status="needs_review"):
        existing = self.get(listing_id)
        if not existing:
            return None
        existing.update(
            {
                "summary": summary,
                "summaryPromptVersion": SUMMARY_PROMPT_VERSION,
                "summaryReviewStatus": status,
                "updatedAt": now_iso(),
            }
        )
        return self.with_rewards(existing)

    def get_points_balance(self):
        return self.points_balance

    def claim_listing(self, listing_id):
        listing = self.get(listing_id)
        if not listing:
            return None

        already_claimed = listing_id in self.claimed_listing_ids
        points = listing["pointsValue"]
        if not already_claimed:
            self.claimed_listing_ids.add(listing_id)
            self.points_balance += points

        return {
            "listing": self.get(listing_id),
            "pointsBalance": self.points_balance,
            "awardedPoints": 0 if already_claimed else points,
            "alreadyClaimed": already_claimed,
        }

    def redeem_reward(self, reward_id):
        reward = next((item for item in REWARDS if item["id"] == reward_id), None)
        if not reward:
            return None
        if self.points_balance < reward["pointsCost"]:
            return {
                "error": "Not enough points to redeem this reward.",
                **rewards_state(self.points_balance),
            }
        self.points_balance -= reward["pointsCost"]
        return {
            "redeemedReward": reward,
            **rewards_state(self.points_balance),
        }


def summarize_listing(listing):
    provider = os.getenv("AI_PROVIDER", "mock").lower()
    prompt = (
        f"Summarize this volunteer listing in one recruiter-friendly sentence: "
        f"{listing['title']} with {listing['organization']} in {listing['location']}."
    )

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI

        client = OpenAI()
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
            input=prompt,
        )
        return response.output_text.strip()

    return (
        f"{listing['title']} with {listing['organization']} is a "
        f"{listing['commitment'].lower()} volunteer opportunity in {listing['location']}."
    )


def create_app(repository=None):
    app = Flask(__name__)
    CORS(app, origins=os.getenv("CLIENT_ORIGIN", "http://localhost:5173"))
    app.config["LISTING_REPOSITORY"] = repository or PostgresListingRepository()

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/init-db")
    def init_db():
        app.config["LISTING_REPOSITORY"].init_schema()
        return jsonify({"status": "initialized"})

    @app.get("/api/listings")
    def list_listings():
        listings = app.config["LISTING_REPOSITORY"].list(
            search=request.args.get("search", "").strip(),
            location=request.args.get("location", "").strip(),
            commitment=request.args.get("commitment", "").strip(),
        )
        return jsonify({"listings": listings})

    @app.post("/api/listings")
    def create_listing():
        listing, errors = validate_listing(request.get_json(silent=True) or {})
        if errors:
            return jsonify({"errors": errors}), 400
        return jsonify(app.config["LISTING_REPOSITORY"].create(listing)), 201

    @app.put("/api/listings/<int:listing_id>")
    def update_listing(listing_id):
        listing, errors = validate_listing(request.get_json(silent=True) or {})
        if errors:
            return jsonify({"errors": errors}), 400
        updated = app.config["LISTING_REPOSITORY"].update(listing_id, listing)
        if not updated:
            return jsonify({"error": "Listing not found."}), 404
        return jsonify(updated)

    @app.delete("/api/listings/<int:listing_id>")
    def delete_listing(listing_id):
        deleted = app.config["LISTING_REPOSITORY"].delete(listing_id)
        if not deleted:
            return jsonify({"error": "Listing not found."}), 404
        return "", 204

    @app.post("/api/listings/<int:listing_id>/summary")
    def generate_summary(listing_id):
        listing = app.config["LISTING_REPOSITORY"].get(listing_id)
        if not listing:
            return jsonify({"error": "Listing not found."}), 404
        summary = summarize_listing(listing)
        return jsonify(app.config["LISTING_REPOSITORY"].save_summary(listing_id, summary))

    @app.get("/api/rewards")
    def get_rewards():
        points_balance = app.config["LISTING_REPOSITORY"].get_points_balance()
        return jsonify(rewards_state(points_balance))

    @app.post("/api/listings/<int:listing_id>/claim")
    def claim_listing(listing_id):
        result = app.config["LISTING_REPOSITORY"].claim_listing(listing_id)
        if not result:
            return jsonify({"error": "Listing not found."}), 404
        return jsonify(result)

    @app.post("/api/rewards/redeem")
    def redeem_reward():
        payload = request.get_json(silent=True) or {}
        result = app.config["LISTING_REPOSITORY"].redeem_reward(payload.get("rewardId"))
        if not result:
            return jsonify({"error": "Reward not found."}), 404
        if result.get("error"):
            return jsonify(result), 400
        return jsonify(result)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("FLASK_RUN_PORT", "5000")))
