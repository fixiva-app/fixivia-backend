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

Login (OTP from API console): `9000000001` master, `9000000002` partner, `9000000003` technician, `9000000004` customer.
