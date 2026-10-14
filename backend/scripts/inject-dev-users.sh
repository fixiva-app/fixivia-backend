#!/usr/bin/env bash
# Local / flavor=dev only. Creates one account per role (idempotent).
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ -d .venv ]]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi
python -m app.dev_users
