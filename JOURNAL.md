# JOURNAL

## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/154

**Issue title:** Health check DB probe passes a raw SQL string, which fails under SQLAlchemy 2.x

**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:**
The database probe in `api/routes/health.py` calls `db.execute("SELECT 1")` with a plain Python string. SQLAlchemy 2.x requires textual SQL to be wrapped explicitly with `sqlalchemy.text()`, so this call raises an `ArgumentError` instead of running the query. Because the health check catches that exception and marks postgres as unhealthy, `GET /health` reports the database as down even when it's fully reachable, which would falsely trip alerting/monitoring on a healthy deployment. A successful fix wraps the raw string in `text()` so the probe executes correctly and only reports "unhealthy" when the database is actually unreachable.

**"Is this right for me?" checklist reasoning:**
[TODO: paste checklist questions/content so this can be filled in accurately]

**Branch name:** fix/154-health-check-raw-sql

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger
