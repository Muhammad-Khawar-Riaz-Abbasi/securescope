# HarvestLink

HarvestLink is a portfolio-quality surplus-food rescue and logistics platform. It connects restaurants and grocers with charities and volunteers so safe food is claimed, routed, and delivered before it expires.

## Why this exists

Food waste is a coordination problem as much as a supply problem. A donor needs a fast, accurate handoff; a charity needs quantity, allergens, and a realistic collection window; volunteers need a route they can trust. HarvestLink makes that chain visible from listing to delivery and measures the result.

## User roles and core workflows

- **Donors** publish surplus with quantity, unit, pickup window, address, dietary tags, and allergens.
- **Charities** browse deterministic matches, reserve available listings, and see the donor's status.
- **Volunteers** browse open routes, claim a route, and follow ordered stops.
- **Dispatchers/admins** review organizations, activity, status, and impact analytics.

Core flow: create listing → match by city/category and earliest expiry → charity reserves → dispatcher assembles stops → volunteer claims route → activity trail and impact update.

## Frontend map (React + TypeScript + Vite)

1. **Landing** — product story, partner proof, and calls to action.
2. **Dashboard** — operational snapshot, listings needing attention, live log, impact ring.
3. **Listings** — filterable available/reserved/completed inventory.
4. **Listing detail** — safety metadata, pickup facts, reservation action.
5. **Create listing** — validated donor publishing form wired to the API.
6. **Organizations** — verified partner directory.
7. **Routes** — open route dispatch board.
8. **Route detail** — stop sequence and volunteer claim flow.
9. **Impact analytics** — rescue velocity chart and category breakdown.
10. **Activity & audit** — append-only operational activity trail.
11. **Settings** — workspace profile and preference seam.
12. **Sign in** — authentication seam/demo entry point.

The UI uses a responsive design system: forest/leaf palette, Fraunces display type, DM Sans body type, cards, pills, empty/error/loading states, hover motion, responsive mobile navigation, accessible labels/buttons, and no paid external service. Google Fonts are optional presentation polish; the application works without an API key or paid provider.

## Architecture

```text
React/Vite SPA ── REST/JSON ── FastAPI ── service boundaries
      │                            ├── MatchingProvider (deterministic local ranking)
      │                            ├── ImpactProvider (transparent assumptions)
      │                            └── Activity recorder (audit trail)
      │                                      │
      └────────────── PostgreSQL (production) / SQLite (local tests) ── SQLAlchemy async
```

The frontend falls back to a small, clearly-marked demo snapshot when the API is unavailable, while all operational screens are wired to the backend API when it is running.

## Data model

- `organizations`: donor, charity, or partner identity and verification.
- `members`: organization membership/role seam.
- `food_listings`: quantity, unit, category, dietary/allergen metadata, pickup window/location, and status.
- `reservations`: charity claims with duplicate protection and quantity bounds.
- `delivery_routes`: volunteer, schedule, route status, distance, and notes.
- `route_stops`: ordered listing destinations and stop status.
- `activity_events`: actor, action, entity, detail, and timestamp for auditability.

All operational IDs are UUID strings, timestamps are timezone-aware, foreign keys use cascading deletes where appropriate, and indexes cover listing status/window, organization, reservation/listing, route status, stop ordering, and activity chronology.

## API endpoints

OpenAPI is available at `/docs` and `/redoc` when the API runs.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Liveness and request ID |
| GET/POST | `/api/v1/organizations` | Directory and create partner |
| GET | `/api/v1/listings` | Match/filter available inventory |
| GET | `/api/v1/listings/{id}` | Listing detail |
| POST | `/api/v1/listings` | Create surplus listing |
| GET | `/api/v1/reservations` | Reservation history |
| POST | `/api/v1/reservations` | Reserve listing |
| GET/POST | `/api/v1/routes` | Route board and route creation |
| POST | `/api/v1/routes/{id}/claim` | Volunteer route claim |
| POST | `/api/v1/routes/{id}/stops` | Add route stop |
| GET | `/api/v1/impact` | Meals, CO₂, water, completion metrics |
| GET | `/api/v1/activity` | Recent audit events |

Responses are Pydantic v2 models; request validation rejects oversized quantities, malformed email addresses, invalid windows, unknown organizations, over-claims, duplicate active reservations, and invalid route claims.

## Local setup

Requirements: Python 3.12+, Node 20+, npm. PostgreSQL is optional for local development.

```bash
cd harvestlink
cp .env.example .env

# API (SQLite fallback)
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000

# In a second terminal
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The API seeds demo organizations, listings, a route, reservation, and audit event on first startup (`SEED_DEMO=true`). To use PostgreSQL, set `DATABASE_URL=postgresql+asyncpg://...` in `.env`; `docker compose up --build` starts PostgreSQL, API, and nginx frontend.

## Security model

- CORS is allowlisted from `CORS_ORIGINS`; never use `*` in production.
- An API-key seam is available via `API_KEY` and `X-API-Key`; leave blank for local demo mode.
- No secrets are committed or logged. Request IDs are returned in `X-Request-ID` for support correlation.
- Bounded Pydantic inputs, status checks, foreign keys, and duplicate reservation protection reduce accidental abuse.
- Authentication/authorization is intentionally a seam: `protect` can be replaced with an OIDC/JWT dependency without changing route contracts. Production should add a real identity provider, role checks, rate limiting, TLS, and secret management.

## Testing and quality

```bash
cd backend
pytest
cd ../frontend
npm run typecheck
npm run build
```

The backend tests cover health/seed behavior, API listing retrieval, duplicate reservation protection, and the deterministic impact provider. The frontend build includes strict TypeScript checking.

## Tradeoffs, limitations, roadmap

This first release favors a dependable local demo over vendor lock-in: matching is deterministic (city/category then earliest pickup expiry), impact uses published assumptions (0.8 kg CO₂ and 200 L water per rescued meal), and route distance is supplied by dispatch rather than a paid maps API. SQLite is convenient for tests; PostgreSQL should be used for concurrent production workloads. Authentication, real notifications, geocoding, route optimization, image uploads, and proof-of-delivery photos are seams rather than claims of production readiness.

Next: role-based auth and invitations, notification adapters, geospatial radius matching, route optimization, offline volunteer mode, cold-chain checks, richer donor/charity reporting, and an organization-level data retention policy.
