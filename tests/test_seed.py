"""Unit tests for seed data and the dev inject entrypoint."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.dev_users import inject_payload, main
from app.models import Base, Partner, Pincode, SaasInvoice, ServiceCategory, User
from app.seed import (
    _seed_geo_and_catalog,
    _seed_invoice,
    _seed_partner_org,
    ensure_dev_users,
    seed_if_empty,
)


@pytest.fixture()
def fresh_db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _counts(db):
    return {
        "users": db.scalar(select(User).limit(1)) is not None
        and len(list(db.scalars(select(User)))),
        "pins": len(list(db.scalars(select(Pincode)))),
        "cats": len(list(db.scalars(select(ServiceCategory)))),
        "partners": len(list(db.scalars(select(Partner)))),
        "invoices": len(list(db.scalars(select(SaasInvoice)))),
    }


def test_ensure_dev_users_skips_accounts_on_prod(fresh_db, monkeypatch):
    monkeypatch.setattr("app.config.settings.flavor", "prod")
    monkeypatch.setattr("app.config.settings.master_mobile", "")
    users = ensure_dev_users(fresh_db)
    assert users == []
    assert fresh_db.scalar(select(User).limit(1)) is None
    # base data still seeds on prod
    assert fresh_db.scalar(select(Pincode).limit(1)) is not None
    assert fresh_db.scalar(select(Partner).limit(1)) is not None


def test_ensure_dev_users_seeds_master_from_env_on_prod(fresh_db, monkeypatch):
    monkeypatch.setattr("app.config.settings.flavor", "prod")
    monkeypatch.setattr("app.config.settings.master_mobile", "919999999999")
    users = ensure_dev_users(fresh_db)
    assert [u.mobile for u in users] == ["919999999999"]
    assert users[0].role == "master_admin"
    # idempotent re-run
    assert [u.mobile for u in ensure_dev_users(fresh_db)] == ["919999999999"]


def test_seed_if_empty_full_then_idempotent(fresh_db):
    seed_if_empty(fresh_db)
    assert _counts(fresh_db) == {
        "users": 4, "pins": 4, "cats": 10, "partners": 1, "invoices": 1,
    }
    sp = fresh_db.scalar(select(User).where(User.mobile == "9000000003"))
    assert sp.partner_id is not None
    seed_if_empty(fresh_db)
    assert _counts(fresh_db) == {
        "users": 4, "pins": 4, "cats": 10, "partners": 1, "invoices": 1,
    }
    # Direct re-runs short-circuit on existing rows (idempotent).
    _seed_geo_and_catalog(fresh_db)
    _seed_geo_and_catalog(fresh_db)
    assert _counts(fresh_db)["pins"] == 4
    assert _counts(fresh_db)["cats"] == 10
    assert _seed_partner_org(fresh_db).id == _seed_partner_org(fresh_db).id


def test_ensure_dev_users_bootstraps_geo_and_org(fresh_db):
    users = ensure_dev_users(fresh_db)
    assert [u.role for u in users] == [
        "master_admin", "partner_owner", "service_partner", "customer",
    ]
    assert fresh_db.scalar(select(Pincode).limit(1)) is not None
    assert fresh_db.scalar(select(Partner).limit(1)) is not None
    again = ensure_dev_users(fresh_db)
    assert [u.id for u in again] == [u.id for u in users]


def test_seed_invoice_guards(fresh_db):
    _seed_invoice(fresh_db)  # no partner yet: no-op
    assert fresh_db.scalar(select(SaasInvoice).limit(1)) is None
    seed_if_empty(fresh_db)
    first = fresh_db.scalar(select(SaasInvoice).limit(1)).id
    _seed_invoice(fresh_db)  # already invoiced: no-op
    assert [r.id for r in fresh_db.scalars(select(SaasInvoice))] == [first]


def test_inject_payload_shape(fresh_db):
    accounts = inject_payload(fresh_db)
    assert len(accounts) == 4
    for acc in accounts:
        assert set(acc) == {"mobile", "role", "full_name", "email", "user", "token"}
        assert acc["user"]["role"] == acc["role"]
        assert acc["token"]


def test_dev_main_guards_flavor(monkeypatch):
    monkeypatch.setattr(settings, "flavor", "prod")
    with pytest.raises(SystemExit, match="not dev"):
        main()


def test_dev_main_runs(capsys):
    main()  # shared DB: idempotent
    out = capsys.readouterr().out
    assert "master_admin" in out and "token" in out


def test_dev_main_as_script(capsys):
    import runpy

    runpy.run_module("app.dev_users", run_name="__main__")
    assert "Dev users" in capsys.readouterr().out
