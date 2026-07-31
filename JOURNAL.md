# JOURNAL

## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/154

**Issue title:** Health check DB probe passes a raw SQL string, which fails under SQLAlchemy 2.x

**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:**
The database probe in `api/routes/health.py` calls `db.execute("SELECT 1")` with a plain Python string. SQLAlchemy 2.x requires textual SQL to be wrapped explicitly with `sqlalchemy.text()`, so this call raises an `ArgumentError` instead of running the query. Because the health check catches that exception and marks postgres as unhealthy, `GET /health` reports the database as down even when it's fully reachable, which would falsely trip alerting/monitoring on a healthy deployment. A successful fix wraps the raw string in `text()` so the probe executes correctly and only reports "unhealthy" when the database is actually unreachable.

**"Is this right for me?" checklist reasoning:**

*Part 1 — Understanding the issue:* The `/health` route calls `db.execute("SELECT 1")` with a bare string. SQLAlchemy 2.x only accepts raw SQL wrapped in `sqlalchemy.text()`, so the call raises `ArgumentError`, which the route's `except Exception` catches and reports as `postgres: "unhealthy"` — even when the database is completely reachable. A correct fix makes the probe run cleanly and report `"healthy"` when Postgres is actually up, `"unhealthy"` only when it's actually down. Affected area: `api/routes/health.py` (label `api`).

*Part 2 — Tier fit:* Labeled `tier-1` in the tracker, and it matches the Tier 1 description — the change lives in one file, is a one-line fix (`text("SELECT 1")`), and doesn't require understanding how modules interact. This is my first contribution to a codebase this size, so Tier 1 is the right level.

*Part 3 — Codebase readiness:* Found and read the exact line (`api/routes/health.py:31`) and the surrounding `try/except` blocks for redis and vector_db, which follow the same pattern. Confirmed `core/database.py` uses the async SQLAlchemy 2.x engine (`create_async_engine`/`AsyncSession`), which is why `text()` is required. There's no existing test file for the health route (`tests/unit` and `tests/integration` have no `health` or `api` test files), so I'll add one — `tests/unit/test_review_service.py` shows the project's pattern for mocking an async db session with `AsyncMock`, which I'll follow.

*Part 4 — Scope and time:* Several others have already commented on the issue and opened PRs against it (this is a practice repo, so duplicate work across the cohort is expected and fine). Scope is small — I already applied and verified the fix locally (confirmed via `GET /health` returning `postgres: "healthy"`), well within the Tier 1 3–6 hour estimate. No blockers or dependencies on other issues.

**Branch name:** fix/154-health-check-raw-sql

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/heyz-hye/pathreview/commit/bbed07a

**Reproduction summary:**
I reproduced the bug by hitting `GET /health` against a reachable Postgres and observing a `503` with `postgres: "unhealthy"`. The raw `db.execute("SELECT 1")` call raised SQLAlchemy 2.x's `ArgumentError` (textual SQL must be wrapped in `text()`), which the route's `except Exception` swallowed and mislabeled as the database being down. Commit `bbed07a` documents and fixes the reproduced issue; `af548af` adds a regression test that fails on the raw-string version and passes after wrapping in `text()`.

**PLAN.md link:** https://github.com/heyz-hye/pathreview/blob/fix/154-health-check-raw-sql/PLAN.md

**Walkthrough video (recommended):** [not recorded]

**Blockers or open questions:**
None blocking. Open follow-up: grep the wider codebase for other raw-string `db.execute("...")` calls that may hit the same SQLAlchemy 2.x issue outside the scope of #154.
