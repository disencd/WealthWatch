"""API tests for the expenses router (/api/v1/expenses)."""

import pytest

from tests.conftest import register_user, auth_header


# ── Helpers ───────────────────────────────────────────────────────

async def _create_expense(client, token, **overrides):
    """Create an expense with sensible defaults; return the response."""
    payload = {
        "title": "Dinner",
        "amount": 60.0,
        "date": "2025-01-15T00:00:00",
        "splits": [],
    }
    payload.update(overrides)
    return await client.post(
        "/api/v1/expenses", json=payload, headers=auth_header(token),
    )


# ── Tests ─────────────────────────────────────────────────────────

async def test_create_expense_with_splits(client):
    """POST /expenses with splits returns 201 and persists splits."""
    data = await register_user(client)
    token = data["token"]
    payer_id = data["user"]["id"]

    # Register a second user to include in splits
    data2 = await register_user(client, email="user2@example.com", first_name="Bob")
    other_id = data2["user"]["id"]

    resp = await _create_expense(
        client, token,
        title="Team lunch",
        amount=100.0,
        date="2025-03-10T00:00:00",
        category="food",
        splits=[
            {"user_id": payer_id, "amount": 50.0, "percentage": 50},
            {"user_id": other_id, "amount": 50.0, "percentage": 50},
        ],
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Team lunch"
    assert body["amount"] == 100.0
    assert "id" in body

    # Verify the expense detail includes splits
    detail = await client.get(
        f"/api/v1/expenses/{body['id']}", headers=auth_header(token),
    )
    assert detail.status_code == 200
    splits = detail.json()["splits"]
    assert len(splits) == 2
    amounts = sorted(s["amount"] for s in splits)
    assert amounts == [50.0, 50.0]


async def test_create_expense_without_splits(client):
    """POST /expenses with no splits returns 201 and empty splits list."""
    data = await register_user(client)
    token = data["token"]

    resp = await _create_expense(
        client, token,
        title="Solo coffee",
        amount=5.50,
        date="2025-02-01T00:00:00",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Solo coffee"
    assert body["amount"] == 5.50

    # Confirm the detail has zero splits
    detail = await client.get(
        f"/api/v1/expenses/{body['id']}", headers=auth_header(token),
    )
    assert detail.status_code == 200
    assert detail.json()["splits"] == []


async def test_list_expenses(client):
    """GET /expenses returns only the current user's expenses, newest first."""
    data = await register_user(client)
    token = data["token"]

    # Create two expenses with different dates
    await _create_expense(client, token, title="Old", amount=10.0, date="2025-01-01T00:00:00")
    await _create_expense(client, token, title="New", amount=20.0, date="2025-06-01T00:00:00")

    resp = await client.get("/api/v1/expenses", headers=auth_header(token))

    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    # Most recent first
    assert items[0]["title"] == "New"
    assert items[1]["title"] == "Old"


async def test_get_expense_by_id(client):
    """GET /expenses/{id} returns the correct expense."""
    data = await register_user(client)
    token = data["token"]

    create_resp = await _create_expense(
        client, token, title="Groceries", amount=45.0, date="2025-04-20T00:00:00",
    )
    expense_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/expenses/{expense_id}", headers=auth_header(token),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == expense_id
    assert body["title"] == "Groceries"
    assert body["amount"] == 45.0
    assert body["payer_id"] == data["user"]["id"]


async def test_get_expense_not_found(client):
    """GET /expenses/{id} returns 404 for a non-existent expense."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/expenses/99999", headers=auth_header(token),
    )
    assert resp.status_code == 404


async def test_unauthenticated_access(client):
    """Endpoints reject requests without a valid token."""
    # No auth header at all
    resp_list = await client.get("/api/v1/expenses")
    assert resp_list.status_code in (401, 403)

    resp_create = await client.post(
        "/api/v1/expenses",
        json={"title": "X", "amount": 1, "date": "2025-01-01T00:00:00"},
    )
    assert resp_create.status_code in (401, 403)

    resp_detail = await client.get("/api/v1/expenses/1")
    assert resp_detail.status_code in (401, 403)


async def test_create_expense_optional_fields(client):
    """POST /expenses honours optional fields (currency, category, description)."""
    data = await register_user(client)
    token = data["token"]

    resp = await _create_expense(
        client, token,
        title="Flight",
        amount=350.0,
        date="2025-05-10T00:00:00",
        currency="EUR",
        category="travel",
        description="Business trip to Berlin",
    )

    assert resp.status_code == 201

    detail = await client.get(
        f"/api/v1/expenses/{resp.json()['id']}", headers=auth_header(token),
    )
    body = detail.json()
    assert body["currency"] == "EUR"
    assert body["category"] == "travel"
