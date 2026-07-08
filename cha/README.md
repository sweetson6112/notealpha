# CHA Bills Approval Note Management System

An enterprise web application for **CDRSL Bond Warehouse** that automates the
preparation of Approval Notes for payment of Customs House Agent (CHA) bills
and Shipping Line reimbursement invoices — eliminating manual, ad-hoc
document drafting.

The generated Approval Note (Word / PDF / Excel / on-screen / print view)
reproduces the layout of the reference sample: header line with document
number + date, bold underlined subject, `Para 1 / 2 / 3 / 4` structure, a
6-column charges table with a bold Total row, and the fixed 5-line signature
block (Sr. Superintendent Duty Free → MD, CDRSL).

## Tech Stack

- **Backend:** Python 3.12, Flask
- **Database:** PostgreSQL (SQLAlchemy ORM). Falls back to local SQLite automatically if `DATABASE_URL` is not set, so the project runs with zero external setup for development/demo purposes.
- **Auth:** Flask-Login, role-based access control (RBAC)
- **Frontend:** Bootstrap 5, Jinja2, Chart.js, vanilla JS
- **Migrations:** Flask-Migrate / Alembic
- **Exports:** python-docx (Word), LibreOffice headless (PDF conversion), openpyxl (Excel)
- **Deployment:** Docker, Gunicorn, Render, Railway

## Quick Start (local, SQLite)

```bash
pip install -r requirements.txt --break-system-packages   # or use a venv
cp .env.example .env                                       # edit as needed
flask db upgrade
python seed.py
python app.py
```

Visit `http://localhost:5000`. Demo accounts (all use password `Password@123`):

| Username    | Role                 |
|-------------|----------------------|
| admin       | Administrator        |
| accounts    | Accounts Officer     |
| bondsupt    | Bond Superintendent  |
| manager     | Manager              |
| finance     | Finance              |
| viewer      | Viewer               |

A demo shipment (File No. `1849`, matching the reference sample) is seeded
with its Approval Note already generated: `CDRSL/BOND/1849/25-26/01`.

## Quick Start (Docker + Postgres)

```bash
docker-compose up --build
```

This starts Postgres and the web app together, runs migrations, seeds demo
data, and serves via Gunicorn on `http://localhost:5000`.

## Deploying

- **Render:** push the repo and use the included `render.yaml` blueprint (Docker-based web service + managed Postgres).
- **Railway:** create a project from the repo, add a Postgres plugin, set `DATABASE_URL` and `SECRET_KEY` env vars, and use `Dockerfile` as the build source.

## Core Workflows

1. **Create a Shipment** (File Number, GRN, BOE, Supplier Invoice Ref, CHA, Shipping Line, etc.). Two default invoices — *Shipping Line Invoice* and *CHA Service Charge* — are auto-created.
2. **Add Invoices** to the shipment (unlimited, any of the 8 supported types), classify each as **Company Borne** (with reason) or **Recoverable** (with recover-from party), and attach supporting documents.
3. **Generate Approval Note** — auto-assigns the document number `CDRSL/BOND/{File Number}/{FY}/{Running No}`, auto-drafts the Subject line and Paragraphs 1/2/4 from the shipment + invoice data, and computes totals.
4. **Review & edit** the auto-generated paragraphs (while status is Draft) before submitting.
5. **Workflow**: Draft → Submitted → Accounts Verification → Manager Approval → Finance Approval → Paid → Completed, with full approval history and role-gated transitions.
6. **Export** the note as Word, PDF, or Excel, or open the dedicated print view — all layouts match the reference sample.

## Project Structure

```
app.py                  Flask application factory / entrypoint
config.py                Environment-based configuration
extensions.py             Shared Flask extension instances
models/                   SQLAlchemy models (Users, Shipments, Invoices, ApprovalNotes, ...)
routes/                   Blueprints: auth, dashboard, shipments, invoices, approval_note, admin, reports, api
services/                 Business logic: doc numbering, paragraph generation, Word/PDF/Excel export, audit log
templates/                Jinja2 templates (Bootstrap 5)
static/                   CSS/JS
migrations/               Alembic migration scripts
uploads/ exports/         Runtime file storage
tests/                    Pytest suite (auth, RBAC, approval note generation)
seed.py                   Demo data seeder
Dockerfile, docker-compose.yml, render.yaml, gunicorn.conf.py   Deployment
```

## Security

- Passwords hashed with Werkzeug's PBKDF2-based `generate_password_hash`
- CSRF protection on all state-changing forms (Flask-WTF)
- Role-based access control via `@roles_required(...)` decorators on routes
- Session cookies are `HttpOnly`, `SameSite=Lax`, with a configurable idle timeout
- SQL injection protection via SQLAlchemy's parameterized queries throughout

## REST API

Session-based JSON API under `/api` (`/api/login`, `/api/users`, `/api/shipments`,
`/api/invoices`, `/api/approval-note`, `/api/reports/summary`). POST `/api/login`
with `{"username": "...", "password": "..."}` to obtain a session cookie for
subsequent calls.

## Notes & Known Limitations

- PDF export relies on LibreOffice headless (`soffice`) being installed on the
  server (included in `Dockerfile`); if unavailable, the export route falls
  back to serving the `.docx` file with a warning message.
- The workflow, RBAC, and approval-note-generation logic are covered by the
  automated tests in `tests/test_basic.py` (`pytest`); further test coverage
  (reports, exports, admin panel) is a natural next step for a production
  rollout.
- Default `SQLALCHEMY_DATABASE_URI` uses local SQLite for a zero-config dev
  experience; set `DATABASE_URL` to your PostgreSQL connection string for
  production (already the default expectation in `docker-compose.yml` /
  `render.yaml`).
