# Bulk Certificate Generator

A backend API that accepts bulk certificate-generation requests and produces
PDF certificates in the background.  Built with **FastAPI**, **SQLAlchemy**,
and **ReportLab**.

---

## Quick start

```bash
# 1. clone & enter the repo
git clone <repo-url>
cd bulk-certificate-generator

# 2. create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. install dependencies
pip install -r requirements.txt

# 4. run the server
uvicorn app.main:app --reload
```

The API is now live at **http://127.0.0.1:8000**.  
Interactive docs: **http://127.0.0.1:8000/docs** (Swagger UI).

---

## How to submit a certificate-generation request

Send a `POST` to `/api/v1/jobs/` with a JSON body:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Certificate of Completion",
    "event_name": "Advanced Python Workshop",
    "event_date": "2024-08-20",
    "issuer_name": "Prof. Alan Turing",
    "recipients": [
      {"name": "Alice Johnson",  "email": "alice@example.com"},
      {"name": "Bob Williams",   "email": "bob@example.com"},
      {"name": "Charlie Brown",  "email": "charlie@example.com"}
    ]
  }'
```

The response returns immediately with the job metadata (status will be
`"pending"` or already `"processing"`).  PDF generation happens in the
background.

### Check job progress

```bash
curl http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

The response includes `status`, `successful_count`, `failed_count`, and
an array of individual certificate records.

### Download a single certificate

```bash
curl -OJ http://127.0.0.1:8000/api/v1/jobs/<job_id>/certificates/<cert_id>/download
```

### Download all certificates as a ZIP

```bash
curl -OJ http://127.0.0.1:8000/api/v1/jobs/<job_id>/download
```

---

## Running the tests

```bash
pytest -v
```

The test suite covers:

| Area | What's tested |
|---|---|
| Job creation | POST returns 201, correct fields |
| Input validation | Missing/blank fields, bad emails, wrong date format, name length |
| Certificate generation | PDF file created, valid magic bytes, reasonable size, long-name handling |
| Job status & progress | Job reaches `completed`, counts are accurate |
| Partial failure | One broken certificate → others still succeed, job is `completed_with_errors` |
| Downloads | Single PDF download, ZIP download, 404 for missing certs |

---

## API reference

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/v1/jobs/` | Create a new generation job |
| `GET` | `/api/v1/jobs/` | List jobs (pagination via `skip` & `limit`) |
| `GET` | `/api/v1/jobs/{id}` | Job detail + certificate statuses |
| `GET` | `/api/v1/jobs/{id}/certificates` | List certificates for a job |
| `GET` | `/api/v1/jobs/{id}/certificates/{cid}/download` | Download one PDF |
| `GET` | `/api/v1/jobs/{id}/download` | Download all completed PDFs as ZIP |
| `GET` | `/` | Health check |

Full interactive docs are available at `/docs` when the server is running.

---

## Project structure

```
.
├── app/
│   ├── main.py                  # FastAPI application entry-point
│   ├── config.py                # centralised settings (env-based)
│   ├── database.py              # engine, session, Base
│   ├── models.py                # Job & Certificate ORM models
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── routers/
│   │   └── certificates.py      # all /api/v1/jobs/… routes
│   └── services/
│       ├── certificate_generator.py   # ReportLab PDF rendering
│       └── job_processor.py           # background worker logic
├── tests/
│   ├── conftest.py
│   ├── test_api.py
│   ├── test_validation.py
│   └── test_generator.py
├── requirements.txt
└── README.md
```

---

## Design decisions

### Why FastAPI?

FastAPI gives us automatic request validation via Pydantic, built-in
OpenAPI docs, and first-class support for `BackgroundTasks` — all of
which map directly to the requirements.

### Synchronous vs. asynchronous processing

Certificate generation is handled **asynchronously** through FastAPI's
`BackgroundTasks`.  The POST endpoint returns immediately with the job
metadata and starts PDF rendering in a background thread.

I chose `BackgroundTasks` + `ThreadPoolExecutor` over Celery because:

- **Zero external infrastructure** — no Redis or RabbitMQ to install.
  The project runs with `pip install` and `uvicorn` alone.
- **Parallel rendering** — the `ThreadPoolExecutor` fans work across
  multiple threads, so PDFs are generated concurrently (configurable via
  the `MAX_WORKERS` env var, default 4).
- **Good enough for the scope** — for a single-server deployment this
  approach is simple and effective.  If the system needed distributed
  workers or retry queues, Celery would be the natural next step.

### Database writes stay on one thread

The thread pool only does CPU work (rendering PDFs).  All SQLAlchemy
writes happen sequentially on the background-task thread.  This avoids
SQLite's "database is locked" errors and keeps the architecture simple.

### Fault tolerance

Each certificate is generated independently.  If one fails (e.g. a
rendering error), the exception is caught, the individual certificate
is marked `"failed"` with an error message, and the remaining
certificates continue.  The job ends up as `"completed_with_errors"`.

### Certificate format

PDFs are generated with **ReportLab** — pure Python, no system-level
dependencies like wkhtmltopdf or Cairo.  The template draws everything
programmatically (borders, typography, ornamental divider) so there are
no external image assets to manage.

### SQLite

SQLite is used as the default database to keep setup friction minimal.
The connection string is configurable via the `DATABASE_URL` env var, so
switching to PostgreSQL is a one-line change.
