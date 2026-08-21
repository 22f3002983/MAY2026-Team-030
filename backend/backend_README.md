# Niwaas — Backend API
### Sprint 1 Deliverable | MAY2026 Team 030 | IIT Madras BS Program

> "Dial a Secretary… Not Anymore."

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Flask 3.0.3 |
| ORM | Flask-SQLAlchemy 3.1.1 |
| Auth | Flask-Login 0.6.3 (session-based) |
| Database | SQLite (dev) |
| Testing | pytest 8.2.2 |
| API Docs | Flasgger + Flask-Swagger-UI |
| PDF Generation | ReportLab |
| Scheduler | APScheduler |

---

## Prerequisites

- Python 3.10 or above
- pip

Verify:
```bash
python --version
pip --version
```

---

## Installation

```bash
# Clone the repository
git clone git@github.com:22f3002983/MAY2026-Team-030.git
cd MAY2026-Team-030/backend

# Install dependencies
pip install -r requirements.txt
```

---

## Running the App

```bash
python run.py
```

The server starts at **http://localhost:5000**

No `.env` file needed — the app runs with safe defaults out of the box.

---

## Seed Test Accounts

After starting the server, run in a new terminal:

```bash
python seed.py
```

This creates two starting accounts:

| Email | Password | Role |
|---|---|---|
| secretary@niwaas.in | test1234 | Secretary |
| resident@niwaas.in | test1234 | Resident |

Additional residents and security accounts are created through the app by the secretary.

---

## API Documentation — Swagger UI

With the server running, open:

```
http://localhost:5000/api/docs
```

This opens the full interactive Swagger UI with all 88 endpoints grouped by module.

Alternatively, paste `swagger.yaml` into **https://editor.swagger.io** to view the documentation without running the server.

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: **36 tests passing** across 5 modules.

| Test File | Module | Tests |
|---|---|---|
| test_auth.py | Authentication | 5 |
| test_vendors.py | Vendors | 5 |
| test_notices.py | Notices | 5 |
| test_emergency.py | Emergency Alerts | 16 |
| test_visitors.py | Visitors | 5 |
| **Total** | | **36** |

---

## Project Structure

```
backend/
├── app/
│   ├── __init__.py         # App factory — blueprints, CORS, db
│   ├── config.py           # Config with env-based settings
│   ├── extensions.py       # SQLAlchemy and Flask-Login instances
│   ├── scheduler.py        # APScheduler — amenity auto-release
│   ├── models/             # 22 SQLAlchemy models
│   │   ├── user.py
│   │   ├── resident.py
│   │   ├── secretary.py
│   │   ├── security.py
│   │   ├── flat.py
│   │   ├── vendor.py
│   │   ├── community_issue.py
│   │   ├── complaint.py
│   │   ├── amenity.py
│   │   ├── booking.py
│   │   ├── notice.py
│   │   ├── emergency.py
│   │   ├── dues.py
│   │   ├── visitor.py
│   │   ├── document_request.py
│   │   ├── profile_update.py
│   │   ├── electricity_bill.py
│   │   ├── notification.py
│   │   ├── service_request.py
│   │   └── fund.py         # FundConfig, SocietyFund, FundTransaction
│   └── routes/             # 15 API blueprints
│       ├── auth.py         # /api/auth
│       ├── complaints.py   # /api/complaints
│       ├── vendors.py      # /api/vendors
│       ├── notices.py      # /api/notices
│       ├── dues.py         # /api/dues
│       ├── emergency.py    # /api/emergency
│       ├── visitors.py     # /api/visitors
│       ├── amenities.py    # /api/amenities
│       ├── summary.py      # /api/summary
│       ├── notifications.py # /api/notifications
│       ├── service_requests.py # /api/service-requests
│       ├── electricity_bills.py # /api/electricity-bills (Sprint 2)
│       ├── funds.py        # /api/funds
│       ├── document_requests.py # /api/document-requests
│       └── profile_requests.py  # /api/profile-requests
├── tests/
│   ├── conftest.py         # Fixtures — in-memory SQLite, role clients
│   ├── test_auth.py
│   ├── test_vendors.py
│   ├── test_notices.py
│   ├── test_emergency.py
│   └── test_visitors.py
├── requirements.txt
├── run.py
├── seed.py
├── swagger.yaml            # OpenAPI 3.0 — 88 endpoints, 15 tags
└── .env.example            # Copy to .env for optional overrides
```

---

## API Modules

| Module | Prefix | Endpoints | User Stories |
|---|---|---|---|
| Auth | /api/auth | 9 | Registration, login, onboarding, invite codes |
| Complaints | /api/complaints | 7 | US-1, US-8, US-11, US-12, US-13 |
| Vendors | /api/vendors | 5 | US-12, US-17 |
| Notices | /api/notices | 4 | US-3, US-5 |
| Dues | /api/dues | 6 | US-14, US-15 |
| Emergency | /api/emergency | 3 | US-9, US-16 |
| Visitors | /api/visitors | 7 | US-6, US-21 to US-26 |
| Amenities | /api/amenities | 11 | US-2 |
| Summary | /api/summary | 2 | Dashboard metrics |
| Notifications | /api/notifications | 4 | In-app bell badge |
| Service Requests | /api/service-requests | 6 | US-7, US-8, US-19 |
| Electricity Bills | /api/electricity-bills | 3 | Sprint 2 — AI analysis |
| Funds | /api/funds | 5 | Society fund management |
| Document Requests | /api/document-requests | 5 | US-4 |
| Profile Requests | /api/profile-requests | 4 | US-10 |

---

## Optional — Environment Variables

Copy `.env.example` to `.env` if you want to override defaults:

```bash
cp .env.example .env
```

| Variable | Default | Purpose |
|---|---|---|
| SECRET_KEY | dev-secret | Flask session signing key |
| DATABASE_URL | sqlite:///niwaas.db | Database connection |
| FLASK_DEBUG | true | Enable debug mode |
| OPENROUTER_API_KEY | (empty) | Sprint 2 — AI features |
| OPENROUTER_MODEL | openai/gpt-oss-20b:free | Sprint 2 — AI model |

---

## Team

| Name | Roll No | Sprint 1 Role |
|---|---|---|
| Humaerah Fatma | 22f3002983 | Notices & Emergency blueprints |
| Jatin Kumar | 23f2005698 | Vendors & Visitors blueprints |
| Sahil Raaj Kapur | 21f1001549 | Flask setup, models, auth, code review |
| Ayushi Munshi | 24f2008412 | Complaints & Amenities blueprints |
| Rajneesh | 23f3002888 | Dues, Documents & Notifications blueprints |

---

*Niwaas · IIT Madras BS Program · MAY2026 Team 030 · Sprint 1*
