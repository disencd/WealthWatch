"""Integration tests for the Auto-Category Rules API (/api/v1/rules)."""

import pytest

from tests.conftest import auth_header, register_user

BASE = "/api/v1/rules"
CATEGORIES_URL = "/api/v1/budget/categories"


# ── helpers ───────────────────────────────────────────────────────


async def _get_category_id(client, headers) -> int:
    """Return the id of the first default category for this family."""
    resp = await client.get(CATEGORIES_URL, headers=headers)
    assert resp.status_code == 200, resp.text
    cats = resp.json()
    assert len(cats) > 0, "Expected at least one default category after registration"
    return cats[0]["id"]


async def _create_rule(client, headers, category_id: int, **overrides) -> dict:
    """POST a rule and return the JSON body."""
    payload = {
        "merchant_pattern": "Amazon*",
        "category_id": category_id,
        "priority": 0,
    }
    payload.update(overrides)
    resp = await client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_rule(client):
    """POST /rules creates a rule and returns 201."""
    data = await register_user(client)
    headers = auth_header(data["token"])
    cat_id = await _get_category_id(client, headers)

    body = {
        "merchant_pattern": "Starbucks*",
        "category_id": cat_id,
        "min_amount": 1.0,
        "max_amount": 50.0,
        "priority": 5,
    }
    resp = await client.post(BASE, json=body, headers=headers)
    assert resp.status_code == 201

    rule = resp.json()
    assert rule["merchant_pattern"] == "Starbucks*"
    assert rule["category_id"] == cat_id
    assert rule["min_amount"] == 1.0
    assert rule["max_amount"] == 50.0
    assert rule["priority"] == 5
    assert rule["is_active"] is True


@pytest.mark.asyncio
async def test_list_rules(client):
    """GET /rules returns all rules for the family."""
    data = await register_user(client)
    headers = auth_header(data["token"])
    cat_id = await _get_category_id(client, headers)

    await _create_rule(client, headers, cat_id, merchant_pattern="Amazon*")
    await _create_rule(client, headers, cat_id, merchant_pattern="Walmart*")

    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 2
    patterns = {r["merchant_pattern"] for r in items}
    assert patterns == {"Amazon*", "Walmart*"}


@pytest.mark.asyncio
async def test_list_rules_ordered_by_priority_desc(client):
    """GET /rules returns rules ordered by priority descending."""
    data = await register_user(client)
    headers = auth_header(data["token"])
    cat_id = await _get_category_id(client, headers)

    await _create_rule(client, headers, cat_id, merchant_pattern="Low", priority=1)
    await _create_rule(client, headers, cat_id, merchant_pattern="High", priority=100)
    await _create_rule(client, headers, cat_id, merchant_pattern="Mid", priority=50)

    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 3
    # Highest priority first
    assert items[0]["merchant_pattern"] == "High"
    assert items[1]["merchant_pattern"] == "Mid"
    assert items[2]["merchant_pattern"] == "Low"


@pytest.mark.asyncio
async def test_update_rule(client):
    """PUT /rules/{id} partially updates a rule."""
    data = await register_user(client)
    headers = auth_header(data["token"])
    cat_id = await _get_category_id(client, headers)

    rule = await _create_rule(client, headers, cat_id, merchant_pattern="Amazon*", priority=0)

    resp = await client.put(
        f"{BASE}/{rule['id']}",
        json={"merchant_pattern": "Amazon.com*", "priority": 10, "is_active": False},
        headers=headers,
    )
    assert resp.status_code == 200

    updated = resp.json()
    assert updated["merchant_pattern"] == "Amazon.com*"
    assert updated["priority"] == 10
    assert updated["is_active"] is False
    # Unchanged
    assert updated["category_id"] == cat_id


@pytest.mark.asyncio
async def test_delete_rule(client):
    """DELETE /rules/{id} removes the rule and returns 204."""
    data = await register_user(client)
    headers = auth_header(data["token"])
    cat_id = await _get_category_id(client, headers)

    rule = await _create_rule(client, headers, cat_id)

    resp = await client.delete(f"{BASE}/{rule['id']}", headers=headers)
    assert resp.status_code == 204

    # Confirm it's gone
    resp = await client.get(BASE, headers=headers)
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_update_not_found(client):
    """PUT /rules/{id} returns 404 for a non-existent id."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.put(f"{BASE}/99999", json={"priority": 1}, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(client):
    """DELETE /rules/{id} returns 404 for a non-existent id."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.delete(f"{BASE}/99999", headers=headers)
    assert resp.status_code == 404
