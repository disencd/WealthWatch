"""API tests for the settlements router (/api/v1/settlements)."""

import pytest

from tests.conftest import register_user, auth_header


# ── Helpers ───────────────────────────────────────────────────────

async def _register_two_users(client):
    """Register two users and return (data_a, data_b) dicts with tokens."""
    data_a = await register_user(client, email="a@example.com", first_name="Alice")
    data_b = await register_user(client, email="b@example.com", first_name="Bob")
    return data_a, data_b


async def _create_settlement(client, token, to_user_id, amount=50.0, **kwargs):
    """Create a settlement and return the response."""
    payload = {"to_user_id": to_user_id, "amount": amount}
    payload.update(kwargs)
    return await client.post(
        "/api/v1/settlements", json=payload, headers=auth_header(token),
    )


# ── Tests ─────────────────────────────────────────────────────────

async def test_create_settlement(client):
    """POST /settlements creates a pending settlement and returns it."""
    data_a, data_b = await _register_two_users(client)

    resp = await _create_settlement(
        client,
        data_a["token"],
        to_user_id=data_b["user"]["id"],
        amount=75.0,
        currency="USD",
        payment_method="venmo",
        notes="Dinner reimbursement",
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["from_user_id"] == data_a["user"]["id"]
    assert body["to_user_id"] == data_b["user"]["id"]
    assert body["amount"] == 75.0
    assert body["status"] == "pending"
    assert body["payment_method"] == "venmo"
    assert body["notes"] == "Dinner reimbursement"
    assert "id" in body


async def test_list_settlements(client):
    """GET /settlements returns settlements where user is sender or receiver."""
    data_a, data_b = await _register_two_users(client)
    token_a = data_a["token"]
    token_b = data_b["token"]
    id_b = data_b["user"]["id"]

    # Alice creates two settlements to Bob
    await _create_settlement(client, token_a, id_b, amount=10.0)
    await _create_settlement(client, token_a, id_b, amount=20.0)

    # Alice sees both (she is from_user)
    resp_a = await client.get("/api/v1/settlements", headers=auth_header(token_a))
    assert resp_a.status_code == 200
    assert len(resp_a.json()) == 2

    # Bob also sees both (he is to_user)
    resp_b = await client.get("/api/v1/settlements", headers=auth_header(token_b))
    assert resp_b.status_code == 200
    assert len(resp_b.json()) == 2


async def test_get_settlement_by_id(client):
    """GET /settlements/{id} returns the correct settlement."""
    data_a, data_b = await _register_two_users(client)
    token_a = data_a["token"]

    create_resp = await _create_settlement(
        client, token_a, data_b["user"]["id"], amount=42.0,
    )
    settlement_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/settlements/{settlement_id}", headers=auth_header(token_a),
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == settlement_id
    assert body["amount"] == 42.0
    assert body["status"] == "pending"


async def test_get_settlement_not_found(client):
    """GET /settlements/{id} returns 404 for non-existent settlement."""
    data = await register_user(client)
    resp = await client.get(
        "/api/v1/settlements/99999", headers=auth_header(data["token"]),
    )
    assert resp.status_code == 404


async def test_update_status_to_completed(client):
    """PUT /settlements/{id}/status transitions to completed."""
    data_a, data_b = await _register_two_users(client)
    token_a = data_a["token"]

    create_resp = await _create_settlement(
        client, token_a, data_b["user"]["id"], amount=100.0,
    )
    settlement_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/settlements/{settlement_id}/status",
        json={"status": "completed"},
        headers=auth_header(token_a),
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    # Confirm persistence
    detail = await client.get(
        f"/api/v1/settlements/{settlement_id}", headers=auth_header(token_a),
    )
    assert detail.json()["status"] == "completed"


async def test_update_status_to_cancelled(client):
    """PUT /settlements/{id}/status transitions to cancelled."""
    data_a, data_b = await _register_two_users(client)
    token_a = data_a["token"]

    create_resp = await _create_settlement(
        client, token_a, data_b["user"]["id"], amount=25.0,
    )
    settlement_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/settlements/{settlement_id}/status",
        json={"status": "cancelled"},
        headers=auth_header(token_a),
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelled"


async def test_update_status_invalid(client):
    """PUT /settlements/{id}/status rejects invalid status values."""
    data_a, data_b = await _register_two_users(client)
    token_a = data_a["token"]

    create_resp = await _create_settlement(
        client, token_a, data_b["user"]["id"], amount=10.0,
    )
    settlement_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/v1/settlements/{settlement_id}/status",
        json={"status": "rejected"},
        headers=auth_header(token_a),
    )

    assert resp.status_code == 400


async def test_unauthenticated_settlement_access(client):
    """Settlement endpoints reject requests without a valid token."""
    resp = await client.get("/api/v1/settlements")
    assert resp.status_code in (401, 403)

    resp = await client.post(
        "/api/v1/settlements",
        json={"to_user_id": 1, "amount": 10.0},
    )
    assert resp.status_code in (401, 403)
