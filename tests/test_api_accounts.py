"""Tests for account CRUD and net-worth API endpoints."""

import pytest

from tests.conftest import register_user, auth_header


# ── Account Creation ──────────────────────────────────────────────


async def test_create_checking_account_is_asset(client):
    """Checking account should default is_asset=True."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Chase",
        "account_name": "Primary Checking",
        "account_type": "checking",
        "balance": 5000,
    }, headers=h)

    assert resp.status_code == 201
    body = resp.json()
    assert body["account_name"] == "Primary Checking"
    assert body["institution_name"] == "Chase"
    assert body["account_type"] == "checking"
    assert body["balance"] == 5000
    assert body["is_asset"] is True
    assert body["is_active"] is True
    assert body["currency"] == "USD"
    assert body["ownership"] == "ours"


async def test_create_credit_card_forces_is_asset_false(client):
    """credit_card type should auto-set is_asset=False even if not specified."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Amex",
        "account_name": "Platinum Card",
        "account_type": "credit_card",
        "balance": 3200,
    }, headers=h)

    assert resp.status_code == 201
    body = resp.json()
    assert body["account_type"] == "credit_card"
    assert body["is_asset"] is False


async def test_create_loan_forces_is_asset_false(client):
    """loan type should auto-set is_asset=False even if caller sends is_asset=True."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.post("/api/v1/accounts", json={
        "institution_name": "SoFi",
        "account_name": "Personal Loan",
        "account_type": "loan",
        "balance": 15000,
        "is_asset": True,
    }, headers=h)

    assert resp.status_code == 201
    assert resp.json()["is_asset"] is False


async def test_create_account_with_ownership(client):
    """Verify custom ownership value is stored."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Vanguard",
        "account_name": "Roth IRA",
        "account_type": "investment",
        "balance": 42000,
        "ownership": "mine",
    }, headers=h)

    assert resp.status_code == 201
    assert resp.json()["ownership"] == "mine"


# ── List / Filter ─────────────────────────────────────────────────


async def test_list_accounts(client):
    """List returns all active accounts for the family."""
    data = await register_user(client)
    h = auth_header(data["token"])

    # create two accounts
    await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 1000,
    }, headers=h)
    await client.post("/api/v1/accounts", json={
        "institution_name": "Ally", "account_name": "Savings",
        "account_type": "savings", "balance": 2000,
    }, headers=h)

    resp = await client.get("/api/v1/accounts", headers=h)
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) == 2
    names = {a["account_name"] for a in accounts}
    assert names == {"Checking", "Savings"}


async def test_list_accounts_filter_by_type(client):
    """Filtering by type returns only matching accounts."""
    data = await register_user(client)
    h = auth_header(data["token"])

    await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 1000,
    }, headers=h)
    await client.post("/api/v1/accounts", json={
        "institution_name": "Amex", "account_name": "Gold Card",
        "account_type": "credit_card", "balance": 500,
    }, headers=h)

    resp = await client.get("/api/v1/accounts", params={"type": "credit_card"}, headers=h)
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) == 1
    assert accounts[0]["account_type"] == "credit_card"


async def test_list_accounts_filter_by_ownership(client):
    """Filtering by ownership returns only matching accounts."""
    data = await register_user(client)
    h = auth_header(data["token"])

    await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Joint Checking",
        "account_type": "checking", "balance": 3000, "ownership": "ours",
    }, headers=h)
    await client.post("/api/v1/accounts", json={
        "institution_name": "Fidelity", "account_name": "My 401k",
        "account_type": "investment", "balance": 80000, "ownership": "mine",
    }, headers=h)

    resp = await client.get("/api/v1/accounts", params={"ownership": "mine"}, headers=h)
    assert resp.status_code == 200
    accounts = resp.json()
    assert len(accounts) == 1
    assert accounts[0]["account_name"] == "My 401k"


# ── Get / Update / Delete ─────────────────────────────────────────


async def test_get_account_by_id(client):
    """GET /accounts/{id} returns the correct account."""
    data = await register_user(client)
    h = auth_header(data["token"])

    create_resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 5000,
    }, headers=h)
    account_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/accounts/{account_id}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["id"] == account_id
    assert resp.json()["account_name"] == "Checking"


async def test_get_account_not_found(client):
    """GET /accounts/{id} returns 404 for non-existent ID."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.get("/api/v1/accounts/99999", headers=h)
    assert resp.status_code == 404


async def test_update_account_balance(client):
    """PUT /accounts/{id} can update balance and name."""
    data = await register_user(client)
    h = auth_header(data["token"])

    create_resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 5000,
    }, headers=h)
    account_id = create_resp.json()["id"]

    resp = await client.put(f"/api/v1/accounts/{account_id}", json={
        "balance": 7500,
        "account_name": "Main Checking",
    }, headers=h)

    assert resp.status_code == 200
    body = resp.json()
    assert body["balance"] == 7500
    assert body["account_name"] == "Main Checking"


async def test_update_account_deactivate(client):
    """Deactivating an account excludes it from the list."""
    data = await register_user(client)
    h = auth_header(data["token"])

    create_resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Old Bank", "account_name": "Closed Savings",
        "account_type": "savings", "balance": 0,
    }, headers=h)
    account_id = create_resp.json()["id"]

    await client.put(f"/api/v1/accounts/{account_id}", json={
        "is_active": False,
    }, headers=h)

    resp = await client.get("/api/v1/accounts", headers=h)
    assert resp.status_code == 200
    assert len(resp.json()) == 0  # deactivated = excluded from list


async def test_delete_account(client):
    """DELETE /accounts/{id} removes the account (204)."""
    data = await register_user(client)
    h = auth_header(data["token"])

    create_resp = await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Old Account",
        "account_type": "checking", "balance": 100,
    }, headers=h)
    account_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/accounts/{account_id}", headers=h)
    assert del_resp.status_code == 204

    # confirm it's gone
    get_resp = await client.get(f"/api/v1/accounts/{account_id}", headers=h)
    assert get_resp.status_code == 404


# ── Net Worth ─────────────────────────────────────────────────────


async def test_networth_summary_mixed_accounts(client):
    """Summary correctly separates assets and liabilities."""
    data = await register_user(client)
    h = auth_header(data["token"])

    # assets
    await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 10000,
    }, headers=h)
    await client.post("/api/v1/accounts", json={
        "institution_name": "Vanguard", "account_name": "Brokerage",
        "account_type": "investment", "balance": 50000,
    }, headers=h)

    # liabilities
    await client.post("/api/v1/accounts", json={
        "institution_name": "Amex", "account_name": "Platinum",
        "account_type": "credit_card", "balance": 2000,
    }, headers=h)
    await client.post("/api/v1/accounts", json={
        "institution_name": "Wells Fargo", "account_name": "Mortgage",
        "account_type": "mortgage", "balance": 300000,
    }, headers=h)

    resp = await client.get("/api/v1/networth/summary", headers=h)
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_assets"] == 60000
    assert body["total_liabilities"] == 302000
    assert body["net_worth"] == 60000 - 302000
    assert body["account_count"] == 4
    assert body["assets_by_type"]["checking"] == 10000
    assert body["assets_by_type"]["investment"] == 50000
    assert body["liabilities_by_type"]["credit_card"] == 2000
    assert body["liabilities_by_type"]["mortgage"] == 300000


async def test_networth_snapshot_creation(client):
    """POST /networth/snapshot captures current totals (201)."""
    data = await register_user(client)
    h = auth_header(data["token"])

    await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 8000,
    }, headers=h)
    await client.post("/api/v1/accounts", json={
        "institution_name": "Amex", "account_name": "Card",
        "account_type": "credit_card", "balance": 1500,
    }, headers=h)

    resp = await client.post("/api/v1/networth/snapshot", headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["total_assets"] == 8000
    assert body["total_liabilities"] == 1500
    assert body["net_worth"] == 6500
    assert "id" in body
    assert "date" in body


async def test_networth_history(client):
    """GET /networth/history returns snapshots in order."""
    data = await register_user(client)
    h = auth_header(data["token"])

    await client.post("/api/v1/accounts", json={
        "institution_name": "Chase", "account_name": "Checking",
        "account_type": "checking", "balance": 5000,
    }, headers=h)

    # take two snapshots (balance changes in between)
    await client.post("/api/v1/networth/snapshot", headers=h)

    await client.put(
        "/api/v1/accounts/1",
        json={"balance": 6000},
        headers=h,
    )
    await client.post("/api/v1/networth/snapshot", headers=h)

    resp = await client.get("/api/v1/networth/history", headers=h)
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 2
    assert history[0]["net_worth"] == 5000
    assert history[1]["net_worth"] == 6000


# ── Auth Guard ────────────────────────────────────────────────────


async def test_unauthenticated_access_returns_403(client):
    """All account endpoints reject unauthenticated requests with 403."""
    endpoints = [
        ("GET", "/api/v1/accounts"),
        ("POST", "/api/v1/accounts"),
        ("GET", "/api/v1/accounts/1"),
        ("PUT", "/api/v1/accounts/1"),
        ("DELETE", "/api/v1/accounts/1"),
        ("GET", "/api/v1/networth/summary"),
        ("GET", "/api/v1/networth/history"),
        ("POST", "/api/v1/networth/snapshot"),
    ]
    for method, path in endpoints:
        resp = await client.request(method, path)
        assert resp.status_code == 403, f"{method} {path} returned {resp.status_code}, expected 403"
