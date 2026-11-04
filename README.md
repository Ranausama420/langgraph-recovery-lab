# Job Reliability Dashboard

Multi-tenant workflow operations dashboard built with Django REST Framework, React, and Redux Toolkit.

Each tenant sees only its own jobs. Operators can create and retry jobs; viewers can inspect jobs and events.

## Run the backend

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python manage.py migrate
    python manage.py runserver

The API is available at http://127.0.0.1:8000/api/. Send X-Tenant-Id and X-User-Role headers. Roles are operator and viewer.

## Run the frontend

    cd frontend
    npm install
    npm run dev

The dashboard includes tenant-scoped job counts, recent jobs, tool selection, status badges, and idempotent job creation.

## Reliability model

Jobs, attempts, and workflow events are persisted separately. unstable_email fails once and can be retried, validation always fails and reaches the dead-letter state, and report succeeds. The tenant plus idempotency key prevents duplicate job creation.
