"""Tests for the investment holdings API (/api/v1/investments)."""

import pytest

from tests.conftest import auth_header, register_user

# ── Helpers ───────────────────────────────────────────────────────


async def _create_account(client, headers: dict, **overrides) -> dict:
    """Create an investment account and return the response JSON."""
    payload = {
        "institution_name": "Fidelity",
        "account_name": "Brokerage",
        "account_type": "investment",
        "balance": 10000,
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/accounts", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _create_holding(client, headers: dict, account_id: int, **overrides) -> dict:
    """Create an investment holding and return the response JSON."""
    payload = {
        "account_id": account_id,
        "symbol": "AAPL",
        "name": "Apple Inc",
        "investment_type": "stock",
        "quantity": 10,
        "cost_basis": 150.0,
        "current_price": 175.0,
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/investments", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Tests ─────────────────────────────────────────────────────────


@pytest.mark.anyio
async def test_create_holding(client):
    """Creating a holding auto-calculates value, gain/loss, and percent."""
    data = await register_user(client)
    h = auth_header(data["token"])

    acc = await _create_account(client, h)
    acc_id = acc["id"]

    resp = await client.post(
        "/api/v1/investments",
        json={
            "account_id": acc_id,
            "symbol": "AAPL",
            "name": "Apple Inc",
            "investment_type": "stock",
            "quantity": 10,
            "cost_basis": 150.0,
            "current_price": 175.0,
        },
        headers=h,
    )
    assert resp.status_code == 201
    body = resp.json()

    # Derived fields
    assert body["current_value"] == 1750.0  # 10 * 175
    assert body["gain_loss"] == 250.0  # 1750 - 1500
    expected_pct = 250.0 / 1500.0 * 100  # ~16.667%
    assert abs(body["gain_loss_percent"] - expected_pct) < 0.01

    # Echo-back fields
    assert body["symbol"] == "AAPL"
    assert body["name"] == "Apple Inc"
    assert body["investment_type"] == "stock"
    assert body["quantity"] == 10
    assert body["account_id"] == acc_id
    assert "id" in body


@pytest.mark.anyio
async def test_list_holdings(client):
    """GET /investments returns all family holdings sorted by symbol."""
    data = await register_user(client)
    h = auth_header(data["token"])
    acc = await _create_account(client, h)
    acc_id = acc["id"]

    await _create_holding(client, h, acc_id, symbol="MSFT", name="Microsoft")
    await _create_holding(client, h, acc_id, symbol="AAPL", name="Apple Inc")

    resp = await client.get("/api/v1/investments", headers=h)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    # Sorted alphabetically by symbol
    assert items[0]["symbol"] == "AAPL"
    assert items[1]["symbol"] == "MSFT"


@pytest.mark.anyio
async def test_portfolio_summary_empty(client):
    """Portfolio summary with zero holdings returns zeroed-out totals."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.get("/api/v1/investments/portfolio", headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_value"] == 0
    assert body["total_cost"] == 0
    assert body["total_gain_loss"] == 0
    assert body["total_gain_loss_percent"] == 0
    assert body["holding_count"] == 0
    assert body["by_type"] == {}


@pytest.mark.anyio
async def test_portfolio_summary_with_holdings(client):
    """Portfolio summary aggregates across multiple holdings and groups by type."""
    data = await register_user(client)
    h = auth_header(data["token"])
    acc = await _create_account(client, h)
    acc_id = acc["id"]

    # Stock: 10 shares @ cost 150, price 175 -> value 1750, cost 1500
    await _create_holding(
        client,
        h,
        acc_id,
        symbol="AAPL",
        name="Apple Inc",
        investment_type="stock",
        quantity=10,
        cost_basis=150.0,
        current_price=175.0,
    )
    # ETF: 5 shares @ cost 300, price 320 -> value 1600, cost 1500
    await _create_holding(
        client,
        h,
        acc_id,
        symbol="VOO",
        name="Vanguard S&P 500",
        investment_type="etf",
        quantity=5,
        cost_basis=300.0,
        current_price=320.0,
    )

    resp = await client.get("/api/v1/investments/portfolio", headers=h)
    assert resp.status_code == 200
    body = resp.json()

    assert body["total_value"] == pytest.approx(3350.0)  # 1750 + 1600
    assert body["total_cost"] == pytest.approx(3000.0)  # 1500 + 1500
    assert body["total_gain_loss"] == pytest.approx(350.0)
    assert body["total_gain_loss_percent"] == pytest.approx(350.0 / 3000.0 * 100)
    assert body["holding_count"] == 2
    assert body["by_type"]["stock"] == pytest.approx(1750.0)
    assert body["by_type"]["etf"] == pytest.approx(1600.0)


@pytest.mark.anyio
async def test_update_holding_recalculates(client):
    """PUT recalculates current_value, gain_loss, and gain_loss_percent."""
    data = await register_user(client)
    h = auth_header(data["token"])
    acc = await _create_account(client, h)
    holding = await _create_holding(
        client,
        h,
        acc["id"],
        quantity=10,
        cost_basis=150.0,
        current_price=175.0,
    )
    holding_id = holding["id"]

    # Update price and quantity
    resp = await client.put(
        f"/api/v1/investments/{holding_id}",
        json={"quantity": 20, "current_price": 200.0},
        headers=h,
    )
    assert resp.status_code == 200
    body = resp.json()

    # new value = 20 * 200 = 4000
    assert body["current_value"] == pytest.approx(4000.0)
    # total cost = 20 * 150 = 3000 (cost_basis unchanged)
    assert body["gain_loss"] == pytest.approx(1000.0)
    assert body["gain_loss_percent"] == pytest.approx(1000.0 / 3000.0 * 100)
    assert body["quantity"] == 20
    assert body["current_price"] == 200.0
    assert body["cost_basis"] == 150.0  # unchanged


@pytest.mark.anyio
async def test_update_holding_cost_basis(client):
    """Updating only cost_basis recalculates derived fields correctly."""
    data = await register_user(client)
    h = auth_header(data["token"])
    acc = await _create_account(client, h)
    holding = await _create_holding(
        client,
        h,
        acc["id"],
        quantity=10,
        cost_basis=100.0,
        current_price=100.0,
    )

    resp = await client.put(
        f"/api/v1/investments/{holding['id']}",
        json={"cost_basis": 80.0},
        headers=h,
    )
    assert resp.status_code == 200
    body = resp.json()

    # value stays 10 * 100 = 1000, cost now 10 * 80 = 800
    assert body["current_value"] == pytest.approx(1000.0)
    assert body["gain_loss"] == pytest.approx(200.0)
    assert body["gain_loss_percent"] == pytest.approx(200.0 / 800.0 * 100)


@pytest.mark.anyio
async def test_delete_holding(client):
    """DELETE returns 204 and the holding disappears from the list."""
    data = await register_user(client)
    h = auth_header(data["token"])
    acc = await _create_account(client, h)
    holding = await _create_holding(client, h, acc["id"])

    resp = await client.delete(f"/api/v1/investments/{holding['id']}", headers=h)
    assert resp.status_code == 204

    # Verify it's gone
    resp = await client.get("/api/v1/investments", headers=h)
    assert resp.status_code == 200
    assert len(resp.json()) == 0


@pytest.mark.anyio
async def test_update_holding_not_found(client):
    """PUT on a non-existent holding returns 404."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.put(
        "/api/v1/investments/99999",
        json={"current_price": 999.0},
        headers=h,
    )
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_delete_holding_not_found(client):
    """DELETE on a non-existent holding returns 404."""
    data = await register_user(client)
    h = auth_header(data["token"])

    resp = await client.delete("/api/v1/investments/99999", headers=h)
    assert resp.status_code == 404


@pytest.mark.anyio
async def test_unauthenticated_access(client):
    """All investment endpoints reject requests without a valid token."""
    endpoints = [
        ("GET", "/api/v1/investments"),
        ("POST", "/api/v1/investments"),
        ("GET", "/api/v1/investments/portfolio"),
        ("PUT", "/api/v1/investments/1"),
        ("DELETE", "/api/v1/investments/1"),
    ]
    for method, url in endpoints:
        resp = await client.request(method, url)
        assert resp.status_code in (401, 403), f"{method} {url} should be 401/403 without auth, got {resp.status_code}"


@pytest.mark.anyio
async def test_create_multiple_types(client):
    """Holdings of different investment_type values are stored correctly."""
    data = await register_user(client)
    h = auth_header(data["token"])
    acc = await _create_account(client, h)
    acc_id = acc["id"]

    types_and_symbols = [
        ("stock", "AAPL"),
        ("bond", "BND"),
        ("etf", "SPY"),
        ("mutual_fund", "VTSAX"),
        ("crypto", "BTC"),
    ]
    for inv_type, symbol in types_and_symbols:
        resp = await client.post(
            "/api/v1/investments",
            json={
                "account_id": acc_id,
                "symbol": symbol,
                "name": f"{symbol} Holding",
                "investment_type": inv_type,
                "quantity": 1,
                "cost_basis": 100.0,
                "current_price": 110.0,
            },
            headers=h,
        )
        assert resp.status_code == 201, f"Failed for type={inv_type}"
        assert resp.json()["investment_type"] == inv_type


@pytest.mark.anyio
async def test_holdings_isolated_between_users(client):
    """Holdings created by one user are not visible to another."""
    # User A
    data_a = await register_user(client, email="alice@example.com", first_name="Alice")
    h_a = auth_header(data_a["token"])
    acc_a = await _create_account(client, h_a, account_name="Alice Brokerage")
    await _create_holding(client, h_a, acc_a["id"], symbol="AAPL")

    # User B
    data_b = await register_user(client, email="bob@example.com", first_name="Bob")
    h_b = auth_header(data_b["token"])

    # User B sees no holdings
    resp = await client.get("/api/v1/investments", headers=h_b)
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    # User B's portfolio is empty
    resp = await client.get("/api/v1/investments/portfolio", headers=h_b)
    assert resp.status_code == 200
    assert resp.json()["holding_count"] == 0
