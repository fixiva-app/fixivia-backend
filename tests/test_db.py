"""Unit tests for DB plumbing: engine config, get_db, CommitRoute."""

import pytest
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

import app.db as db_mod
from app.db import CommitRoute, SessionLocal, get_db, init_db


def test_init_db_idempotent_and_backfills_columns():
    init_db()
    init_db()  # second run hits existing-column ALTERs; must not raise
    with db_mod.engine.connect() as conn:
        prod_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(products)")]
        otp_cols = [r[1] for r in conn.exec_driver_sql("PRAGMA table_info(otp_codes)")]
    assert "image_key" in prod_cols
    assert "booking_id" in otp_cols


def test_memory_engine_uses_static_pool_and_busy_timeout():
    assert isinstance(db_mod.engine.pool, StaticPool)
    with db_mod.engine.connect() as conn:
        assert conn.exec_driver_sql("PRAGMA busy_timeout").scalar() == 30000


def _request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def test_get_db_commits_and_closes():
    gen = get_db(_request())
    db = next(gen)
    assert db is not None
    with pytest.raises(StopIteration):
        next(gen)


def test_get_db_rolls_back_on_error():
    req = _request()
    gen = get_db(req)
    db = next(gen)
    assert req.state._db_session is db
    with pytest.raises(RuntimeError, match="boom"):
        gen.throw(RuntimeError("boom"))


def _commit_app() -> FastAPI:
    app = FastAPI()
    app.router.route_class = CommitRoute

    @app.get("/ok")
    def ok():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise HTTPException(500, "x")

    @app.get("/soft-fail")
    def soft_fail():
        return Response(status_code=500)

    return app


def test_commit_route_success_without_session():
    with TestClient(_commit_app()) as client:
        r = client.get("/ok")
        assert r.status_code == 200


def test_commit_route_reraises_without_session():
    with TestClient(_commit_app(), raise_server_exceptions=False) as client:
        r = client.get("/boom")
        assert r.status_code == 500


def test_commit_route_skips_commit_on_error_status():
    with TestClient(_commit_app()) as client:
        r = client.get("/soft-fail")
        assert r.status_code == 500


def test_commit_route_rolls_back_on_handler_error():
    rolled_back = []

    app = FastAPI()
    app.router.route_class = CommitRoute

    @app.get("/x")
    def x(request: Request):
        request.state._db_session = type(
            "FakeSession", (), {"rollback": lambda self: rolled_back.append(1)}
        )()
        raise HTTPException(500, "x")

    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/x").status_code == 500
    assert rolled_back == [1]


def test_commit_route_commits_with_session():
    committed = []

    app = FastAPI()
    app.router.route_class = CommitRoute

    @app.get("/x")
    def x(request: Request):
        request.state._db_session = type(
            "FakeSession", (), {"commit": lambda self: committed.append(1)}
        )()
        return {"ok": True}

    with TestClient(app) as client:
        assert client.get("/x").status_code == 200
    assert committed == [1]
