import os
from datetime import datetime, timezone

import psycopg2
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from psycopg2.extras import RealDictCursor

load_dotenv()

SUMMARY_PROMPT_VERSION = "listing-summary-v1"


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
        "createdAt": row.get("created_at").isoformat() if row.get("created_at") else None,
        "updatedAt": row.get("updated_at").isoformat() if row.get("updated_at") else None,
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
        sql = f"SELECT * FROM listings {where} ORDER BY created_at DESC, id DESC;"
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, values)
                return [row_to_listing(row) for row in cur.fetchall()]

    def get(self, listing_id):
        with connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM listings WHERE id = %s;", (listing_id,))
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
        return list(reversed(results))

    def get(self, listing_id):
        return next((listing for listing in self.listings if listing["id"] == listing_id), None)

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
        return created

    def update(self, listing_id, listing):
        existing = self.get(listing_id)
        if not existing:
            return None
        existing.update({**listing, "updatedAt": now_iso()})
        return existing

    def delete(self, listing_id):
        existing = self.get(listing_id)
        if not existing:
            return False
        self.listings.remove(existing)
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
        return existing


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

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1", port=int(os.getenv("FLASK_RUN_PORT", "5000")))
