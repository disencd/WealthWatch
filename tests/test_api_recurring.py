"""Integration tests for the Recurring Transactions API (/api/v1/recurring)."""

from datetime import datetime, timedelta

import pytest

from tests.conftest import auth_header, register_user

BASE = "/api/v1/recurring"


# ── helpers ───────────────────────────────────────────────────────


def _future(days: int) -> str:
    """Return an ISO-8601 date string *days* from now."""
    return (datetime.utcnow() + timedelta(days=days)).date().isoformat()


async def _create_recurring(client, headers, **overrides) -> dict:
    """POST a recurring transaction and return the JSON body."""
    payload = {
        "merchant": "Netflix",
        "amount": 15.99,
        "currency": "USD",
        "frequency": "monthly",
        "next_due_date": _future(10),
        "notes": "",
    }
    payload.update(overrides)
    resp = await client.post(BASE, json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_recurring(client):
    """POST /recurring creates a recurring transaction and returns 201."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    body = {
        "merchant": "Spotify",
        "amount": 9.99,
        "frequency": "monthly",
        "next_due_date": _future(7),
    }
    resp = await client.post(BASE, json=body, headers=headers)
    assert resp.status_code == 201

    rec = resp.json()
    assert rec["merchant"] == "Spotify"
    assert rec["amount"] == 9.99
    assert rec["frequency"] == "monthly"
    assert rec["is_active"] is True
    assert rec["currency"] == "USD"  # default


@pytest.mark.asyncio
async def test_list_recurring(client):
    """GET /recurring returns all recurring for the family."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    await _create_recurring(client, headers, merchant="Netflix")
    await _create_recurring(client, headers, merchant="Spotify", amount=9.99)

    resp = await client.get(BASE, headers=headers)
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 2
    merchants = {i["merchant"] for i in items}
    assert merchants == {"Netflix", "Spotify"}


@pytest.mark.asyncio
async def test_upcoming_within_30_days(client):
    """GET /recurring/upcoming returns active items due within 30 days."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    # Due in 5 days -- should appear
    await _create_recurring(client, headers, merchant="Hulu", next_due_date=_future(5))
    # Due in 20 days -- should also appear
    await _create_recurring(client, headers, merchant="Disney+", next_due_date=_future(20))

    resp = await client.get(f"{BASE}/upcoming", headers=headers)
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 2
    merchants = [i["merchant"] for i in items]
    assert "Hulu" in merchants
    assert "Disney+" in merchants


@pytest.mark.asyncio
async def test_upcoming_excludes_beyond_30_days(client):
    """GET /recurring/upcoming does NOT include items due > 30 days out."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    # Due in 5 days -- should appear
    await _create_recurring(client, headers, merchant="Hulu", next_due_date=_future(5))
    # Due in 60 days -- should NOT appear
    await _create_recurring(client, headers, merchant="FarAway", next_due_date=_future(60))

    resp = await client.get(f"{BASE}/upcoming", headers=headers)
    assert resp.status_code == 200

    items = resp.json()
    assert len(items) == 1
    assert items[0]["merchant"] == "Hulu"


@pytest.mark.asyncio
async def test_upcoming_excludes_inactive(client):
    """GET /recurring/upcoming excludes inactive recurring items."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    rec = await _create_recurring(client, headers, merchant="CancelledSub", next_due_date=_future(5))

    # Deactivate it
    await client.put(f"{BASE}/{rec['id']}", json={"is_active": False}, headers=headers)

    resp = await client.get(f"{BASE}/upcoming", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_update_recurring(client):
    """PUT /recurring/{id} partially updates a recurring transaction."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    rec = await _create_recurring(client, headers, merchant="Netflix", amount=15.99)

    resp = await client.put(
        f"{BASE}/{rec['id']}",
        json={"amount": 22.99, "frequency": "yearly"},
        headers=headers,
    )
    assert resp.status_code == 200

    updated = resp.json()
    assert updated["amount"] == 22.99
    assert updated["frequency"] == "yearly"
    # Unchanged fields stay the same
    assert updated["merchant"] == "Netflix"


@pytest.mark.asyncio
async def test_delete_recurring(client):
    """DELETE /recurring/{id} removes the item and returns 204."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    rec = await _create_recurring(client, headers)

    resp = await client.delete(f"{BASE}/{rec['id']}", headers=headers)
    assert resp.status_code == 204

    # Confirm it's gone
    resp = await client.get(BASE, headers=headers)
    assert len(resp.json()) == 0


@pytest.mark.asyncio
async def test_update_not_found(client):
    """PUT /recurring/{id} returns 404 for a non-existent id."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.put(f"{BASE}/99999", json={"amount": 1.0}, headers=headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_not_found(client):
    """DELETE /recurring/{id} returns 404 for a non-existent id."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.delete(f"{BASE}/99999", headers=headers)
    assert resp.status_code == 404
