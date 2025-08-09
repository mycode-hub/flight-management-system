
# Implementation Prompt — Real-Time Flight Management System (Backend Only)

**Purpose:**  
Build a production-ready, real-time **backend** for a flight management / booking system (initial scope: backend only). The payment flow will be **mocked** (random success/failure). The system must prevent overbooking, support concurrent bookings, and be extensible to real-time notifications later.

---

# 1. Summary & Goals

**Primary goals**
- Provide a reliable backend for flight search and booking.
- Ensure **no overbooking** (strong consistency for seat counts).
- Support high concurrency and scale horizontally.
- Provide an **Admin** API for adding/updating flights and seat capacities.
- Use Redis as a cache for fast search & seat availability.
- Provide a mock payment service with randomized results to simulate success/failure and latency.
- Make the system testable, observable, and deployable (Docker + optional Kubernetes manifests).

**Assumptions (from diagram)**
- No seat selection UI (we only track number of seats).
- Overbooking is **not allowed**.
- Admins can add/remove flights, set capacity, and view real-time seat counts.
- Data Models:
  - Flight: `{ flight_id, from, to, date, total_seats, available_seats, price }`
  - Booking: `{ booking_id, user_id, flight_id, date, number_of_seats, status }`

---

# 2. High-Level Architecture / Components

1. **API Gateway (FastAPI)** - single entry point that routes to microservices or monolith endpoints.
2. **Flight Search Service** - read-optimized endpoints, uses Redis cache and fallback to DB.
3. **Booking Service** - core booking workflow, handles concurrency, integrates with payment mock, updates DB and cache.
4. **Admin Service** - add / update flights, set seat capacity, triggers cache updates.
5. **Flight DB** - PostgreSQL (production) or SQLite for quick dev; stores canonical flight data.
6. **Booking DB** - PostgreSQL (can be same DB with different tables).
7. **Redis Cache** - caches flight search results and provides atomic seat counters for quick checks.
8. **Mock Payment Service** - returns success/failure randomly with configurable latency.
9. **Cache Populator / Sync** - background process to populate Redis from the DB and subscribe to changes.
10. **Optional Event Bus** - Kafka / Redis Streams to broadcast booking events (recommended for later).
11. **CI / CD** - GitHub Actions for build/test; Docker for containerization.

---

# 3. Data Models (Detailed)

## 3.1 Relational DB (Postgres) Schemas (initial DDL)

```sql
-- flights table
CREATE TABLE flights (
  id UUID PRIMARY KEY,
  flight_number TEXT,
  source TEXT NOT NULL,
  destination TEXT NOT NULL,
  departure_ts TIMESTAMP WITH TIME ZONE NOT NULL,
  arrival_ts TIMESTAMP WITH TIME ZONE,
  total_seats INT NOT NULL,
  available_seats INT NOT NULL,
  price NUMERIC(10,2) NOT NULL,
  version BIGINT DEFAULT 1, -- for optimistic locking
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- bookings table
CREATE TABLE bookings (
  id UUID PRIMARY KEY,
  user_id UUID NOT NULL,
  flight_id UUID REFERENCES flights(id),
  seats INT NOT NULL,
  status TEXT NOT NULL, -- PENDING, CONFIRMED, CANCELLED, FAILED
  payment_ref TEXT,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- booking_intents (optional)
CREATE TABLE booking_intents (
  id UUID PRIMARY KEY,
  booking_id UUID REFERENCES bookings(id),
  expires_at TIMESTAMP WITH TIME ZONE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);
```

## 3.2 Redis Key Design (Improved Event-Driven Model)

- `flight:{flight_id}` — **Hash** of flight details for fast lookups.
- `search:{source}:{destination}:{date}:{sort_criteria}` — **Sorted Set** of `flight_id`s, scored by price or departure time for server-side sorting.
- `flight_seats:{flight_id}` — **String**, used as an atomic integer counter for available seats.
- `lock:flight:{flight_id}` — (Optional for future use) Distributed lock key for complex operations.
- `booking_event_stream` — (Optional for future use) Stream/topic to publish booking events.

---

# 4. API Specification (OpenAPI style)

> All endpoints return JSON. Use JWT for auth (later). For dev, no auth or simple API key.

## Admin Service
- `POST /admin/flights` — Add flight. Triggers an event to populate the Redis cache.
- `PUT /admin/flights/{flight_id}` — Update flight. Triggers an event to invalidate and update the cache.
- `DELETE /admin/flights/{flight_id}` — Remove flight. Triggers an event to remove from the cache.
- `GET /admin/flights/{flight_id}` — View flight details.

## Flight Search Service
- `GET /search` — Query flights.
  - Query params: `source`, `destination`, `date`, `sort` (price|fastest), `limit` (default 20)
  - Responses: list of flights constructed from Redis Hashes and Sorted Sets.

## Booking Service
- `POST /booking` — Create booking intent + start payment.
  - Body: `{ user_id, flight_id, seats }`
  - Flow:
    1. Validate input.
    2. Atomically check and decrement seat availability from `flight_seats:{flight_id}` key in Redis.
    3. Create DB booking with `status=PENDING`.
    4. Initiate payment (call mock payment service).
    5. Return request accepted (202) or synchronous 200 depending on design.
- `POST /payment/callback` — Payment service calls this with `{ booking_id, status, payment_ref }`.
- `GET /booking/{booking_id}` — Get booking status.

## Health & Debug
- `GET /health`
- `GET /metrics` — Prometheus metrics.

---

# 5. Booking Workflow — Step-by-step (Recommended Implementation)

**1. Client POST /booking with flight_id and seats.**  
**2. Input validation** (seats > 0, flight exists).  
**3. Read available seats from Redis: `GET flight_seats:{flight_id}`.**  
**4. If seats available < requested, return 400 / OUT_OF_STOCK.**  
**5. Use a Redis pipeline with `WATCH` on the `flight_seats` key to ensure an atomic transaction.**  
**6. Atomically decrement the seat counter** (`DECRBY`) and update the `available_seats` in the corresponding flight Hash (`HINCRBY`). If the transaction fails due to a `WatchError`, release the lock and return 409.
**7. Create a booking in DB with `status = PENDING` (in a DB transaction).**  
**8. Publish `booking_intent.created` event to event bus (optional).**  
**9. Initiate payment** (HTTP call to mock payment service). The mock will wait a random delay and return success/fail. The booking creation should contain a payment reference.  
**10a. If payment succeeds** → update booking to `CONFIRMED`, set `payment_ref`. Persist and publish `booking.confirmed`. Ensure DB and cache are consistent.  
**10b. If payment fails or times out** → update booking to `FAILED` or `CANCELLED`. Perform compensating action: atomically increase Redis `flight_seats` counter and `available_seats` in the Hash to restore seats, publish `booking.cancelled`.  
**11. Return final status to client (or allow client to poll booking status).**

**Notes:**  
- This Redis-first approach is extremely fast and scalable. The database is updated as the source of truth, but the real-time availability checks are offloaded entirely to Redis.

---

# 6. Concurrency & Consistency Strategies

**Chosen Strategy: Redis-First with Event-Driven Cache Invalidation**
- **Real-time Availability:** A Redis string `flight_seats:{flight_id}` serves as the atomic source of truth for seat counts, managed by `DECRBY`/`INCRBY` commands within transactions.
- **Fast Lookups:** Flight data is stored in Redis Hashes, and search indexes are maintained in Sorted Sets.
- **Data Consistency:** The application logic itself is responsible for keeping the Redis cache consistent with the PostgreSQL database. Any admin action that modifies flight data triggers a corresponding update in Redis, ensuring the cache doesn't become stale.
- **Database as Source of Truth:** While Redis handles the real-time operations, the database remains the durable, canonical source of truth.

---

# 7. Mock Payment Service Behavior

**Endpoints**
- `POST /mock_payment/pay` — Accepts `{ booking_id, amount }`. Returns `{ payment_id, status }`.
- Payment logic:
  - Sleep random delay between X and Y ms (configurable).
  - Randomly return `success` or `failure` (probability configurable).
  - Optionally send callback to `/payment/callback` endpoint on Booking Service.

**Configurables**
- success_rate (default 75%)
- min_delay_ms, max_delay_ms

---

# 8. Cache Strategy and Cache Populator

**Event-Driven Cache Management**
- The system does **not** use a simple TTL-based cache populator.
- **On Admin Actions:** When an admin creates, updates, or deletes a flight via the API:
    1. The database is updated first.
    2. A dedicated `redis_service` is called to perform the corresponding action in Redis.
    3. This includes creating/updating the flight's Hash, adding/removing its ID from the search-related Sorted Sets, and setting/deleting the seat counter.
- **On Startup (Optional but Recommended):** A background job could run on startup to ensure Redis is fully synchronized with the database, in case of a server restart.
- **Data Flow:** For searches, Redis is the primary source. For bookings, Redis is the gatekeeper for availability, while the database remains the system of record.

---

# 9. Observability & Telemetry

**Metrics (Prometheus)**
- bookings_total, bookings_success, bookings_failed, bookings_pending
- redis_decrements_total, redis_decrements_failed
- flight_db_updates_total
- request_latency_seconds

**Tracing (OpenTelemetry)**
- Trace booking flow across services: booking request → payment → db update.

**Logging**
- Structured logs in JSON with correlation IDs for each request (generate X-Request-Id).

---

# 10. Testing Strategy

**Unit tests**
- Business logic: seat decrement, booking state transitions, payment mock behaviours.

**Integration tests**
- Start DB + Redis (docker-compose) and run full booking flow end-to-end.

**Load tests**
- Use locust or k6 to simulate high concurrency booking of same flight to validate no overbooking.

**Chaos testing**
- Simulate payment latency/failure; Redis node restarts; DB primary failover.

---

# 11. Dev / Run / Deploy

**Local dev stack (docker-compose)**
- Services: api (FastAPI), mock-payment, postgres, redis, admin CLI, background worker.
- Volumes for DB.

**Dockerfile (example for a service)**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock /app/
RUN pip install --upgrade pip
RUN pip install fastapi uvicorn[standard] sqlalchemy asyncpg aioredis pydantic
COPY . /app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Kubernetes**
- Deployments & Services for each microservice
- Use Horizontal Pod Autoscaler on CPU or custom metrics
- Use managed Postgres and Redis in prod

---

# 12. CI / CD (GitHub Actions) — Simple pipeline

- `ci.yml`:
  - Jobs: lint, unit-tests, build-docker-image (optional), push to GitHub Container Registry.
- `deploy.yml`:
  - On release or main branch push: build image, update k8s manifests or deploy via Helm.

---

# 13. Security & Best Practices

- Validate all inputs and return proper HTTP status codes.
- Use parameterized SQL queries / ORM (SQLAlchemy) to avoid SQL injection.
- Rate-limit booking endpoints to avoid abuse.
- Secrets (DB credentials, JWT keys) stored in environment variables / secret manager.
- Ensure idempotency for payment callbacks (use payment_ref/payload idempotency key).

---

# 14. Roadmap & Milestones (Issues)

**Milestone 0 — Project Init**
- Create repo skeleton, README, code style, LICENSE.
- Add Dockerfile, docker-compose, .gitignore.

**Milestone 1 — Core DB + Admin**
- Implement Postgres models + migrations.
- Implement Admin API: create/update flights.
- Add flight cache populator.

**Milestone 2 — Flight Search + Cache**
- Implement search endpoints with Redis-backed results.
- Add cache invalidation on admin changes.

**Milestone 3 — Booking Flow (MVP)**
- Implement booking endpoint with Redis atomic reservation + DB booking intent (PENDING).
- Implement mock payment service.
- Implement payment callback handling and finalize booking (CONFIRMED / FAILED).
- Reconciliation job.

**Milestone 4 — Tests & Load**
- Unit & integration tests, load tests to validate concurrency.

**Milestone 5 — Observability & Deployment**
- Add Prometheus metrics and tracing.
- Add GitHub Actions CI and deployment scripts.
- Dockerize all services & provide K8s manifests.

**Milestone 6 — Optional**
- Add Kafka for events, WebSocket notifications.
- Swap mock payment with real payment provider.

Each milestone should have 4–10 issues. Each issue should contain:
- Title
- Description
- Acceptance criteria
- Est. time (dev + test)

---

# 15. GitHub Repo: Steps to Create & Push (Script & Instructions)

> I cannot push to your GitHub account directly. Below is a ready-to-run script and the exact commands to create a private repo using GitHub CLI and push the initial scaffold.

**Prereqs**
- `git`, `gh` (GitHub CLI), Docker (optional).
- `gh auth login` or `GH_TOKEN` environment variable.

**Script: create_repo_and_push.sh**
```bash
#!/usr/bin/env bash
set -e

REPO_NAME="${1:-flight-backend}"
REPO_DESC="Real-time Flight Management Backend (initial skeleton)"
GITHUB_ORG_OR_USER="${2:-$USER}"  # pass org if required

# Create local repo skeleton
mkdir -p "$REPO_NAME"
cd "$REPO_NAME"
git init
cat > README.md <<'MD'
# Flight Backend (Real-time)

This repo contains the backend services for a real-time flight management system.
MD

cat > .gitignore <<'MD'
__pycache__/
venv/
.env
*.pyc
.DS_Store
.envrc
MD

mkdir -p services db cache models scripts infra tests

# Add the initial prompt file (implementation_prompt.md)
# Note: replace this path with where you saved the file locally before running script.
cp ../implementation_prompt.md .

git add .
git commit -m "chore: init repo skeleton and implementation prompt"

# Create private repo on GitHub and push
if gh repo create "$GITHUB_ORG_OR_USER/$REPO_NAME" --private --description "$REPO_DESC" --confirm; then
  git branch -M main
  git remote add origin "git@github.com:$GITHUB_ORG_OR_USER/$REPO_NAME.git"
  git push -u origin main
else
  echo "gh repo create failed. Create repository manually or check your auth."
fi
```

**How to run**
1. Save the script to `create_repo_and_push.sh`.
2. Make executable: `chmod +x create_repo_and_push.sh`.
3. Ensure `implementation_prompt.md` (this file) is in the parent directory where you run script.
4. Run: `./create_repo_and_push.sh flight-backend your-github-username-or-org`

If you prefer HTTPS remote (instead of SSH), edit the `git remote add origin` line accordingly.

---

# 16. CLI Agent Input (Single-file deliverable)
This entire markdown file (the current file) is *the* input artifact for the CLI agent. The agent should:

1. Parse sections and create GitHub issues for the Milestones and Tasks.
2. Create repository structure and populate files.
3. Add CI workflow YAML to `.github/workflows/ci.yml`.
4. Create Dockerfiles and docker-compose for local dev.
5. Scaffold basic FastAPI endpoints and models (Admin, Search, Booking, Mock Payment).
6. Run unit tests and report failures.
7. Create badges in README and set repository visibility to private.

---

# 17. Acceptance Criteria (for MVP release)
- [ ] Able to add flights via Admin API and have them appear in Search.
- [ ] Booking endpoint prevents overbooking under concurrent load (simulate 200 concurrent users).
- [ ] Mock payment randomly succeeds/fails; booking finalizes appropriately.
- [ ] Redis-based fast availability checks return consistent results.
- [ ] Unit and integration tests exist and pass on CI.
- [ ] Dockerized services run via docker-compose for local dev.

---

# 18. Additional Resources & Hints

- For Redis atomic check-and-decrement: use Lua scripts to keep operations atomic.
- For distributed locks: consider `redis-py` RedLock implementation, or client libraries like `aioredis`.
- For DB migrations: use Alembic (SQLAlchemy) or Flyway.
- For async FastAPI DB access: use `SQLModel` or `SQLAlchemy` + `asyncpg`.
- To load test concurrency: k6 or locust.
- Keep the booking logic idempotent to handle retries.

---

# 19. Next Steps (what I can do for you)
- I can scaffold the repo and produce the initial code (FastAPI skeleton, DB models, Redis wrapper, mock payment) and place them in a downloadable ZIP.
- I can generate GitHub Actions CI YAML, Dockerfiles, and docker-compose.
- I can produce the initial set of GitHub issues in markdown ready to import using GitHub API.

---

# 20. Contact / Notes

If you'd like, tell me:
- Which language/framework you prefer? (Default: Python + FastAPI)
- Whether to use synchronous DB operations or async (async recommended).
- Whether to prefer Redis-first or DB-first strategy for the first iteration.

----

*End of implementation prompt.*
