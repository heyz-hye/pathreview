## Solution plan

**Issue:** Health check DB probe passes a raw SQL string, which fails under SQLAlchemy 2.x — [#154](https://github.com/ascherj/pathreview/issues/154)

### Understand

The postgres probe in the `/health` route runs `await db.execute("SELECT 1")`, passing a
bare Python string. SQLAlchemy 2.x removed implicit autoconversion of raw string SQL: any
textual statement must be wrapped in `sqlalchemy.text()`, otherwise `Connection.execute()`
raises `ArgumentError: Textual SQL expression 'SELECT 1' should be explicitly declared as
text('SELECT 1')`.

The route wraps the probe in `try/except Exception`, so that `ArgumentError` is swallowed
and postgres is marked `"unhealthy"`, which also flips the overall `status` to `"unhealthy"`
and makes `GET /health` return `503`.

- **Expected:** `GET /health` reports `postgres: "healthy"` and returns `200` when the
  database is reachable; `"unhealthy"` / `503` only when it is genuinely down.
- **Actual:** `GET /health` reports `postgres: "unhealthy"` and returns `503` on *every*
  request, even against a fully reachable database, because the probe itself never executes.

Root cause: the probe's SQL is not wrapped in `text()`, so it fails at the SQLAlchemy layer
before the query ever reaches Postgres.

### Map

Files, functions, and modules involved:

- `api/routes/health.py` — `health_check()`, the postgres probe on line ~35 (the raw
  `db.execute("SELECT 1")` call). **Primary change.**
- `core/database.py` — confirms the app uses the async SQLAlchemy 2.x stack
  (`create_async_engine` / `AsyncSession`), which is *why* `text()` is required. Read-only
  reference, no change.
- `tests/unit/test_health.py` — new test file (none existed for this route). Follows the
  `AsyncMock` session-mocking pattern from `tests/unit/test_review_service.py`.

Files I expect to touch: `api/routes/health.py`, `tests/unit/test_health.py`.

### Plan

Concrete sub-tasks:

1. **Import the helper.** Add `from sqlalchemy import text` to `api/routes/health.py`.
2. **Wrap the probe.** Change `await db.execute("SELECT 1")` to
   `await db.execute(text("SELECT 1"))` so the statement is a valid `TextClause`.
3. **Add regression tests.** Create `tests/unit/test_health.py` that mocks the async
   session and asserts (a) `db.execute` is called with a non-string `TextClause` whose
   text is `"SELECT 1"`, and (b) postgres is reported `"healthy"` when the probe succeeds.
4. **Verify locally.** Run the app and confirm `GET /health` returns `200` with
   `postgres: "healthy"`; run `pytest tests/unit/test_health.py`.
5. **Document & commit.** Commit the fix referencing `Fixes #154`, and update `JOURNAL.md`.

### Inputs & outputs

- **Input:** an `AsyncSession` injected via `Depends(get_db)`; the SQL statement passed to
  `db.execute()`.
- **Output / change:** the probe now sends a `text("SELECT 1")` `TextClause` instead of a
  raw `str`. On success, `health_status["dependencies"]["postgres"]` becomes `"healthy"`
  and the endpoint returns `200`. On a real outage the existing `except` path still marks
  it `"unhealthy"` and returns `503`. No change to the response schema or the redis /
  vector_db probes.

### Risks & unknowns

- **Other raw-string probes.** Only the postgres probe uses `db.execute`; redis and
  vector_db use their own clients, so no other `text()` wrapping is needed — verified by
  reading `api/routes/health.py` end to end.
- **Test import path for `settings`.** The route imports `settings` locally inside each
  probe (`from core.config import settings`), so the test patches `core.config.settings`
  rather than a module-level attribute — confirmed against the source.
- **Behavior on genuine DB failure.** The fix must not hide real outages. The `except`
  branch is unchanged, so an actual connection error still surfaces as `"unhealthy"` / `503`.
- **Unknown:** whether other routes elsewhere in the codebase pass raw SQL strings to
  `execute()`. Out of scope for #154, but worth a follow-up grep (`db.execute("`).

### Edge cases

The fix should handle these gracefully:

1. **Database genuinely down** — `db.execute(text(...))` raises a connection error; the
   `except` block reports `postgres: "unhealthy"` and the endpoint returns `503`. (Correct
   behavior preserved.)
2. **Postgres healthy but redis or vector_db down** — postgres reports `"healthy"` while
   overall `status` still flips to `"unhealthy"`; the postgres fix must not mask an
   unhealthy sibling dependency.
3. **`vector_db_url` unset** — vector_db is reported `"unavailable"` (not `"unhealthy"`),
   so a missing optional dependency does not force a `503`.
4. **Probe returns but result is unused** — the fix only cares that `execute()` runs
   without raising; the `SELECT 1` result set is intentionally discarded.
