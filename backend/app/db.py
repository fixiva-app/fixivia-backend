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
    connect_args = {"check_same_thread": False}
    if ":memory:" in settings.database_url:
        engine_kwargs["poolclass"] = StaticPool

engine = create_engine(settings.database_url, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


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
