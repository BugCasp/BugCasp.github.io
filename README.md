# Bug Bounty Platform — MVP

A complete, self-contained Startup Bug Bounty Platform with three roles
(**SuperAdmin**, **Startup / Company**, **Hacker**), built with FastAPI +
SQLAlchemy + SQLite on the backend and a Tailwind CSS single-page app on
the frontend (no build step required).

## Features

- JWT authentication with role-based access control (SuperAdmin, Company, Hacker)
- Dual registration flow (Hacker profile vs. Company profile)
- SuperAdmin approval workflow for companies and bug bounty programs
- Program creation with scope, rules of engagement, and severity-based rewards
- Vulnerability report submission with CWE/OWASP category, CVSS v3 score,
  PoC steps, impact analysis, and HTTP payload
- Report triage workflow (`New → Triaged → Resolved/Duplicate/Informative/Not Applicable`)
- Automatic reputation point awards on resolution
- Public leaderboard / Hall of Fame
- Global SuperAdmin analytics dashboard
- Single-file Tailwind CSS SPA frontend served directly by FastAPI

## Requirements

- Python 3.10+
- pip

## Setup & Run

```bash
# 1. Move into the project directory
cd bugbounty_platform

# 2. (Recommended) create a virtual environment
python3 -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Then open your browser at **http://localhost:8000**.

The SQLite database file (`bugbounty.db`) is created automatically in the
project root on first run — no manual migration step is needed.

## Default SuperAdmin Account

On first startup, if no SuperAdmin exists yet, one is seeded automatically:

```
username: admin
password: AdminPass123!
```

**Change this immediately** if you deploy this anywhere beyond local
development — either log in and rely on your own operational process to
rotate the password, or set the following environment variables before
the first run to control the seeded credentials:

```bash
export BUGBOUNTY_ADMIN_USERNAME="youradmin"
export BUGBOUNTY_ADMIN_EMAIL="you@example.com"
export BUGBOUNTY_ADMIN_PASSWORD="a-much-stronger-password"
export BUGBOUNTY_SECRET_KEY="a-long-random-secret-for-jwt-signing"
```

## Typical Workflow

1. **Company** registers via "Get Started → Startup / Company". Their
   account is created immediately, but they cannot create programs until
   approved.
2. **SuperAdmin** logs in (`admin` / `AdminPass123!`) and approves the
   company from the Admin Dashboard.
3. **Company** creates a Bug Bounty Program (target URL, scope, rewards).
   The program is created with `is_approved = False`.
4. **SuperAdmin** approves the program from the Admin Dashboard so it
   becomes publicly visible.
5. **Hacker** registers, browses the Target Explorer, reviews the scope
   of an approved program, and submits a vulnerability report with a
   CVSS score, PoC steps, and impact analysis.
6. **Company** reviews the report in their dashboard and updates its
   status. Marking a report **Resolved** automatically awards reputation
   points to the hacker (severity-based defaults: Low = 10, Medium = 25,
   High = 50, Critical = 100 — or a custom point value can be sent by the
   client).
7. **Hacker** climbs the public **Leaderboard / Hall of Fame** based on
   accumulated reputation points.
8. **SuperAdmin** can also directly arbitrate/override any report's
   status from the global "All Reports" audit view, to resolve disputes
   between companies and hackers.

## Project Structure

```
bugbounty_platform/
│
├── app/
│   ├── __init__.py
│   ├── config.py             # JWT secret, DB URL, application settings
│   ├── database.py           # SQLAlchemy engine and SessionLocal
│   ├── models.py             # ORM database models (User, Company, Program, Report)
│   ├── schemas.py            # Pydantic v2 request/response validation models
│   ├── auth.py               # Password hashing, JWT creation/verification, role dependencies
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth_router.py    # Login, Register, Profile (/me)
│   │   ├── admin_router.py   # Admin management and approval endpoints
│   │   ├── company_router.py # Program creation and company report triage
│   │   └── hacker_router.py  # Scope browsing, report submissions, leaderboard
│   └── main.py               # FastAPI instance, CORS, router inclusion, static mounts
│
├── static/
│   └── index.html            # Complete Tailwind CSS SPA UI with dynamic tab routing
│
├── requirements.txt          # Complete Python dependency list
└── README.md
```

## API Overview

All endpoints are prefixed with `/api`.

| Area | Method & Path | Description |
|---|---|---|
| Auth | `POST /api/auth/register` | Register a Hacker or Company (`account_type` field) |
| Auth | `POST /api/auth/login` | Log in, returns JWT |
| Auth | `GET /api/auth/me` | Current user profile |
| Admin | `GET /api/admin/pending-companies` | Companies awaiting approval |
| Admin | `POST /api/admin/approve-company/{id}` | Toggle company approval |
| Admin | `GET /api/admin/pending-programs` | Programs awaiting approval |
| Admin | `POST /api/admin/approve-program/{id}` | Toggle program approval |
| Admin | `GET /api/admin/all-reports` | Audit view of all reports |
| Admin | `PUT /api/admin/reports/{id}/status` | Arbitrate/override a report's status |
| Admin | `GET /api/admin/analytics` | Global platform analytics |
| Company | `POST /api/company/programs` | Create a program (requires approved company) |
| Company | `GET /api/company/my-programs` | List own programs |
| Company | `GET /api/company/programs/{id}/reports` | Reports for one of your programs |
| Company | `PUT /api/company/reports/{id}/status` | Update report status, auto-award reputation on Resolve |
| Hacker | `GET /api/hacker/programs` | Public list of approved & active programs |
| Hacker | `GET /api/hacker/programs/{id}` | Program scope detail |
| Hacker | `POST /api/hacker/reports` | Submit a vulnerability report |
| Hacker | `GET /api/hacker/my-reports` | Your own submitted reports |
| Hacker | `GET /api/hacker/leaderboard` | Public Hall of Fame |

Interactive API docs are also available at **http://localhost:8000/docs**
(Swagger UI, auto-generated by FastAPI).

## Security Notes (MVP scope)

- Passwords are hashed with bcrypt via `passlib`.
- JWTs are signed with HS256; set `BUGBOUNTY_SECRET_KEY` in production.
- Role checks are enforced server-side via FastAPI dependencies on every
  protected route — the frontend UI hiding/showing tabs is a convenience
  only, not a security boundary.
- This MVP uses SQLite for zero-configuration local execution. For a real
  production deployment, swap `BUGBOUNTY_DATABASE_URL` for a Postgres/MySQL
  connection string — the SQLAlchemy models require no changes.
