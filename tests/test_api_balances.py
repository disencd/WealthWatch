"""API tests for the balances router (/api/v1/balances)."""

from tests.conftest import auth_header, register_user

# ── Helpers ───────────────────────────────────────────────────────


async def _create_expense_with_splits(client, token, payer_id, split_user_id, amount, split_amount):
    """Create an expense where *payer_id* pays and *split_user_id* owes *split_amount*."""
    return await client.post(
        "/api/v1/expenses",
        json={
            "title": "Shared expense",
            "amount": amount,
            "date": "2025-01-15T00:00:00",
            "splits": [
                {"user_id": split_user_id, "amount": split_amount},
            ],
        },
        headers=auth_header(token),
    )


# ── Tests ─────────────────────────────────────────────────────────


async def test_empty_balances(client):
    """GET /balances returns an empty list when no expenses exist."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get("/api/v1/balances", headers=auth_header(token))

    assert resp.status_code == 200
    assert resp.json() == []


async def test_balances_after_expense_with_splits(client):
    """GET /balances reflects money owed via splits."""
    # User A pays, User B owes a split
    data_a = await register_user(client, email="a@example.com", first_name="Alice")
    data_b = await register_user(client, email="b@example.com", first_name="Bob")

    token_a = data_a["token"]
    id_a = data_a["user"]["id"]
    id_b = data_b["user"]["id"]

    # Alice pays $100, Bob's split is $60
    resp = await _create_expense_with_splits(client, token_a, id_a, id_b, 100.0, 60.0)
    assert resp.status_code == 201

    # From Alice's perspective, Bob owes her $60
    bal_resp = await client.get("/api/v1/balances", headers=auth_header(token_a))
    assert bal_resp.status_code == 200
    balances = bal_resp.json()
    assert len(balances) == 1
    assert balances[0]["user_id"] == id_b
    assert balances[0]["balance"] == 60.0

    # From Bob's perspective, he owes Alice $60 (negative balance)
    bal_resp_b = await client.get("/api/v1/balances", headers=auth_header(data_b["token"]))
    assert bal_resp_b.status_code == 200
    balances_b = bal_resp_b.json()
    assert len(balances_b) == 1
    assert balances_b[0]["user_id"] == id_a
    assert balances_b[0]["balance"] == -60.0


async def test_balance_with_specific_user(client):
    """GET /balances/users/{id} returns detailed breakdown for one user."""
    data_a = await register_user(client, email="a@example.com", first_name="Alice")
    data_b = await register_user(client, email="b@example.com", first_name="Bob")

    token_a = data_a["token"]
    token_b = data_b["token"]
    id_a = data_a["user"]["id"]
    id_b = data_b["user"]["id"]

    # Alice pays $100, Bob owes $40
    await _create_expense_with_splits(client, token_a, id_a, id_b, 100.0, 40.0)

    # Bob pays $80, Alice owes $30
    await _create_expense_with_splits(client, token_b, id_b, id_a, 80.0, 30.0)

    # Alice checks balance with Bob
    resp = await client.get(
        f"/api/v1/balances/users/{id_b}",
        headers=auth_header(token_a),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == id_b
    assert body["they_owe_you"] == 40.0  # Bob's split on Alice's expense
    assert body["you_owe_them"] == 30.0  # Alice's split on Bob's expense
    assert body["net_balance"] == 10.0  # 40 - 30


async def test_balance_with_nonexistent_user(client):
    """GET /balances/users/{id} returns 404 for unknown user."""
    data = await register_user(client)
    token = data["token"]

    resp = await client.get(
        "/api/v1/balances/users/99999",
        headers=auth_header(token),
    )
    assert resp.status_code == 404
