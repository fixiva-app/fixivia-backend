"""Unit tests for model helpers."""

import uuid
from datetime import datetime, timezone

from app.models import as_utc_aware, new_id, utcnow


def test_utcnow_is_aware_utc():
    now = utcnow()
    assert now.tzinfo is not None
    assert now.utcoffset().total_seconds() == 0


def test_as_utc_aware_branches():
    naive = datetime(2026, 1, 2, 3, 4, 5)
    aware = as_utc_aware(naive)
    assert aware.tzinfo == timezone.utc
    assert aware.replace(tzinfo=None) == naive
    same = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    assert as_utc_aware(same) is same


def test_new_id_unique_uuids():
    a, b = new_id(), new_id()
    assert a != b
    uuid.UUID(a)
    uuid.UUID(b)
