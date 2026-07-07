# VolunteerHub

VolunteerHub is a CUHacking 2025 student project for managing volunteer opportunities. The app lets a user create, edit, delete, search, filter, claim points from, and redeem rewards for listings from a React frontend, with data persisted by a Flask API backed by PostgreSQL.

The project also includes an optional AI-assisted listing summary workflow. It defaults to a mock summary provider so the app runs without API keys.

## Tech Stack

- Frontend: React 19, TypeScript, Vite, Tailwind CSS
- Backend: Python, Flask, Flask-CORS
- Database: PostgreSQL, Docker Compose for local development
- Tests: Vitest, React Testing Library, pytest
- CI: GitHub Actions

## Screenshots

![Volunteer listings dashboard](docs/screenshots/listings-dashboard.png)

![AI-assisted listing summary](docs/screenshots/listing-summary.png)

## Folder Structure

```text
.
├── client/                 # React/Vite frontend
│   ├── src/components/      # UI components and listing manager
│   ├── src/test/            # Vitest setup
│   └── package.json
├── server/                 # Flask backend
│   ├── backend.py           # API routes, PostgreSQL repository, mock test repository
│   ├── requirements.txt
│   └── tests/               # pytest API tests
├── docker-compose.yml       # Local PostgreSQL service
├── docs/screenshots/        # README screenshots
├── .github/workflows/       # CI workflow
├── .env.example             # Backend environment template
└── README.md
```

## Environment Variables

Copy the examples before running locally:

```bash
cp .env.example .env
cp client/.env.example client/.env
```

Backend variables:

```text
DATABASE_URL=postgresql://user:password@localhost:5432/volottdb
FLASK_RUN_PORT=5000
CLIENT_ORIGIN=http://localhost:5173
AI_PROVIDER=mock
OPENAI_API_KEY=
```

Frontend variables:

```text
VITE_API_BASE_URL=http://localhost:5000
VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
VITE_FIREBASE_MEASUREMENT_ID=
```

Firebase values are only needed for Google sign-in. Listing management works without them.

## Setup

Install frontend dependencies:

```bash
cd client
npm install
```

Install backend dependencies:

```bash
cd server
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Database Setup

Start PostgreSQL with Docker Compose:

```bash
docker compose up -d postgres
```

Then start the backend and initialize the schema in another terminal:

```bash
cd server
flask --app backend run --port 5000
```

In another terminal:

```bash
curl -X POST http://localhost:5000/api/init-db
```

The app creates a `listings` table with fields for listing details, generated summary text, prompt version, and human review status.

If you already have PostgreSQL installed locally, you can skip Docker and create a database that matches `DATABASE_URL`:

```bash
createdb volottdb
```

## Run Locally

Start the backend:

```bash
cd server
source .venv/bin/activate
flask --app backend run --port 5000
```

Start the frontend:

```bash
cd client
npm run dev
```

Open `http://localhost:5173`.

## Tests

Frontend:

```bash
cd client
npm test
npm run test:coverage
```

Backend:

```bash
cd server
pytest
pytest --cov=backend --cov-report=term-missing
```

The backend tests use an in-memory repository, so they do not require PostgreSQL.
PostgreSQL integration tests run when `POSTGRES_TEST_DATABASE_URL` is set:

```bash
cd server
POSTGRES_TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/volunteerhub_test pytest
```

Coverage reports are also printed in GitHub Actions so changes can be compared over time.

### API Benchmark

With the Flask API running, measure listing-read latency and reliability:

```bash
cd server
python -m benchmarks.benchmark_api --requests 100 --concurrency 10
```

The JSON report includes request throughput, error rate, and average, p50, p95, and p99 latency. Run the same command against the same dataset before and after an optimization so the comparison stays honest.

## Optional AI Summary Workflow

By default, `AI_PROVIDER=mock` generates a deterministic local summary. To use OpenAI instead:

```text
AI_PROVIDER=openai
OPENAI_API_KEY=your_key_here
```

Generated summaries are stored on the listing with:

- `summary`
- `summaryPromptVersion`
- `summaryReviewStatus`

New AI summaries are marked `needs_review`.

### Summary Evaluation

Run the deterministic mock-provider baseline:

```bash
cd server
AI_PROVIDER=mock python -m evals.evaluate_summaries --samples 50
AI_PROVIDER=mock python -m evals.evaluate_summaries --samples 50 --min-success-rate 100 --min-field-coverage 100
```

The report records provider, prompt version, generation success rate, required-field coverage, and average/p95 latency. The field metric checks whether title, organization, commitment, and location remain present; it is a narrow grounding check, not a complete measure of writing quality or hallucination risk.
GitHub Actions runs the thresholded mock evaluation so prompt changes cannot silently lower the baseline.

## Rewards Flow

Listings have a point value based on their commitment level. Users can claim points once per listing, see their current reward balance, and redeem prototype gift card rewards when they have enough points.

This is intentionally lightweight gamification for the demo. It uses a shared demo user rather than production authentication or real gift card fulfillment.

## Known Limitations

- Authentication is still basic Firebase sign-in plumbing and is not connected to listing permissions.
- Rewards use a shared demo user and prototype gift card states; there is no real payment or fulfillment integration.
- The UI is intentionally simple and student-project realistic, not a production admin dashboard.
- The previous scraper route was removed from the main workflow; listing data is currently entered through the app.
