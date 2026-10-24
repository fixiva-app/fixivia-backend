"""Postgres-dialect branches: compile checks without a live PG server."""

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from app.db import SessionLocal
from app.jobs.dispatch_job import _is_pg
from app.models import BookingOffer, ServicePartnerProfile, User


def test_is_pg_false_on_sqlite():
    db = SessionLocal()
    try:
        assert _is_pg(db) is False
    finally:
        db.close()


def test_offer_upsert_compiles_on_both_dialects():
    values = [{"booking_id": "b", "service_partner_id": "s"}]
    for module, dialect in ((sqlite, sqlite.dialect()),
                            (postgresql, postgresql.dialect())):
        stmt = (
            module.insert(BookingOffer)
            .values(values)
            .on_conflict_do_update(
                index_elements=["booking_id", "service_partner_id"],
                set_={"last_notified_at": None},
            )
        )
        sql = str(stmt.compile(dialect=dialect))
        assert "ON CONFLICT" in sql


def test_profile_order_compiles_on_postgres():
    stmt = select(User.id).order_by(ServicePartnerProfile.user_id)
    sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "ORDER BY" in sql
