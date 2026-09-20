# Fixvia / Fixiva

Geographic home-services SaaS. **Checklist:** [docs/CHECKLIST.md](docs/CHECKLIST.md)

| Path | Stack |
|------|--------|
| `frontend/` | Flutter (web, iOS, Android) |
| `backend/` | FastAPI + SQLAlchemy |
| `docs/` | Requirements + HTML briefing |

```bash
cd backend && source .venv/bin/activate && pytest && uvicorn app.main:app --reload --port 8080
cd frontend && flutter test && flutter run -d chrome --dart-define=API_BASE=http://127.0.0.1:8080
```

Login (OTP from API console, or debug “enter as” chips):

- `9000000001` Master Admin
- `9000000002` Partner owner
- `9000000003` Technician
- `9000000004` Customer
- `9000000005` Partner admin

Inject / refresh those five users (idempotent, **flavor=dev only**):

```bash
./scripts/inject-dev-users.sh
# or: cd backend && python -m app.dev_users
# or: curl -X POST http://127.0.0.1:8080/v1/dev/inject-users
```
