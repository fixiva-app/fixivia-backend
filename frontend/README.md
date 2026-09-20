# Fixvia frontend

Single Flutter app (Android, iOS, web). Role after login selects a shell. Visual brand is **Fixiva**.

```bash
cd frontend
flutter pub get
flutter test
flutter run -d chrome --dart-define=FLAVOR=dev --dart-define=API_BASE=http://127.0.0.1:8080
```

- Theme: `lib/shared/theme/`
- Shared widgets: `lib/shared/widgets/` (`testId` → `Key` + Semantics identifier)
- Screens: `lib/features/`
- EN + ML: `lib/l10n/`
- Logos: `assets/branding/` (from `docs/branding/Fixiva logos/`)

See `docs/Req/17-frontend.md` and `docs/Req/18-branding.md`.
