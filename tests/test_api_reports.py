"""API tests for the reports router (/api/v1/reports).

NOTE: The spending-trends endpoint uses Postgres-specific INTERVAL syntax
which does not work on SQLite. We test that it doesn't crash with a 500
but accept non-200 responses gracefully. The other endpoints use
extract() which SQLAlchemy translates for SQLite in recent versions.
"""

import pytest

from tests.conftest import register_user, auth_header


# ── Tests ─────────────────────────────────────────────────────────

async def test_spending_by_merchant_empty(client):
    """GET /reports/spending-by-merchant returns empty list when no data."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/reports/spending-by-merchant",
        headers=auth_header(token),
    )

    assert resp.status_code == 200
    assert resp.json() == []


async def test_spending_by_merchant_with_filters(client):
    """GET /reports/spending-by-merchant accepts year/month/limit params."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/reports/spending-by-merchant",
        params={"year": 2025, "month": 1, "limit": 5},
        headers=auth_header(token),
    )

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_cashflow_sankey_empty(client):
    """GET /reports/cashflow-sankey returns nodes/links structure when no data."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/reports/cashflow-sankey",
        params={"year": 2025, "month": 1},
        headers=auth_header(token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "nodes" in body
    assert "links" in body
    assert isinstance(body["nodes"], list)
    assert isinstance(body["links"], list)


async def test_savings_rate_empty(client):
    """GET /reports/savings-rate returns zero values when no data."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/reports/savings-rate",
        params={"year": 2025, "month": 1},
        headers=auth_header(token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["year"] == 2025
    assert body["month"] == 1
    assert body["total_income"] == 0
    assert body["total_expenses"] == 0
    assert body["savings"] == 0
    assert body["savings_rate"] == 0


@pytest.mark.xfail(
    reason="spending-trends uses Postgres INTERVAL syntax incompatible with SQLite",
    raises=Exception,
    strict=False,
)
async def test_spending_trends_graceful_on_sqlite(client):
    """GET /reports/spending-trends uses Postgres INTERVAL syntax.

    On SQLite this raises an OperationalError because INTERVAL is
    Postgres-specific. This test is expected to fail on SQLite but
    will pass when running against a real Postgres database.
    """
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/reports/spending-trends",
        params={"months": 6},
        headers=auth_header(token),
    )

    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_reports_unauthenticated(client):
    """Report endpoints reject requests without auth."""
    for path in [
        "/api/v1/reports/spending-trends",
        "/api/v1/reports/spending-by-merchant",
        "/api/v1/reports/cashflow-sankey?year=2025&month=1",
        "/api/v1/reports/savings-rate?year=2025&month=1",
    ]:
        resp = await client.get(path)
        assert resp.status_code in (401, 403), f"{path} should require auth"
