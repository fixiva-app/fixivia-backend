# Fixvia backend

FastAPI. SQLite file `fixvia.db` locally (Postgres URL later). Dispatch runs as FastAPI BackgroundTasks; `POST /v1/jobs/dispatch-repool` is the 3-hour job.

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload --port 8080
```

Seeded OTP login mobiles (check console for codes):

- `9000000001` Master Admin
- `9000000002` Partner owner
- `9000000003` Technician
- `9000000004` Customer
- `9000000005` Partner admin

If the database already existed before partner-admin was added, inject one of each role (dev only, safe to re-run):

```bash
./scripts/inject-dev-users.sh
# or: python -m app.dev_users
# or POST http://127.0.0.1:8080/v1/dev/inject-users
```

OTP prints as `[OTP] purpose=login ... code=......`
