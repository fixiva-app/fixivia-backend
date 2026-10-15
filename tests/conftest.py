import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["SEED_ON_START"] = "true"

from fastapi.testclient import TestClient

from app.main import app


def make_client() -> TestClient:
    return TestClient(app)


_STARTED = {"t": 0.0}


def pytest_sessionstart(session):
    import time

    _STARTED["t"] = time.time()


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    import time

    stats = terminalreporter.stats
    passed = len(stats.get("passed", []))
    failed = len(stats.get("failed", []))
    errors = len(stats.get("error", []))
    skipped = len(stats.get("skipped", []))
    deselected = len(stats.get("deselected", []))
    total = passed + failed + errors + skipped
    elapsed = time.time() - _STARTED["t"]

    tw = terminalreporter
    tw.section("backend unit test report", sep="=")
    tw.line(f"total: {total}   passed: {passed}   failed: {failed}   "
            f"errors: {errors}   skipped: {skipped}   "
            f"deselected: {deselected}   time: {elapsed:.1f}s")
    verdict = "PASS" if (failed == 0 and errors == 0 and total > 0) else "FAIL"
    tw.line(f"result: {verdict}")
    tw.line("")
    tw.line(f"{'test file':<32}{'passed':>8}{'failed':>8}{'skipped':>9}")
    per_file: dict = {}
    for outcome in ("passed", "failed", "error", "skipped"):
        for rep in stats.get(outcome, []):
            fname = rep.nodeid.split("::")[0].replace("tests/", "")
            row = per_file.setdefault(fname, {"passed": 0, "failed": 0, "skipped": 0})
            row["failed" if outcome in ("failed", "error") else
                "skipped" if outcome == "skipped" else "passed"] += 1
    for fname in sorted(per_file):
        row = per_file[fname]
        tw.line(f"{fname:<32}{row['passed']:>8}{row['failed']:>8}{row['skipped']:>9}")
