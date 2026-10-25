from __future__ import annotations

from collections.abc import Callable, Generator

from fastapi import Request
from fastapi.responses import Response
from fastapi.routing import APIRoute
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models import Base

connect_args = {}
engine_kwargs: dict = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
    if ":memory:" in settings.database_url:
        engine_kwargs["poolclass"] = StaticPool
else:
    # Remote DB (Supabase Postgres, possibly via pgbouncer): recycle dead
    # pooled connections instead of failing the first query on them.
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _record) -> None:
        # Background pool writes race request writes; WAL + a long busy
        # timeout turn "database is locked" 500s into brief waits.
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA busy_timeout=30000")
        cur.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # create_all never adds columns to existing tables. Best-effort ALTERs
    # for columns added after first release; ignored when the column
    # already exists (fresh DBs) or the write races another boot.
    from sqlalchemy import text

    for table, column, ddl in (
        ("otp_codes", "booking_id", "VARCHAR(36)"),  # TEMP-OTP
        ("products", "image_key", "VARCHAR(200)"),  # R2 object key
    ):
        try:
            with engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
        except Exception:
            pass


def get_db(request: Request) -> Generator[Session, None, None]:
    db = SessionLocal()
    request.state._db_session = db
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


class CommitRoute(APIRoute):
    """Commit the request DB session before the response is sent.

    FastAPI runs BackgroundTasks after the response is sent and tears down
    yield-dependencies (get_db's commit) only after that. Without this,
    background work such as the dispatch pool, and the client's immediate
    next request, can run before this request's writes are committed.
    """

    def get_route_handler(self) -> Callable[[Request], Response]:
        handler = super().get_route_handler()

        async def _handler(request: Request) -> Response:
            try:
                response = await handler(request)
            except Exception:
                db = getattr(request.state, "_db_session", None)
                if db is not None:
                    db.rollback()
                raise
            if response.status_code < 400:
                db = getattr(request.state, "_db_session", None)
                if db is not None:
                    db.commit()
            return response

        return _handler
