"""Tests for the Budget API (/api/v1/budget)."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_header, register_user

BASE = "/api/v1/budget"

DEFAULT_CATEGORY_NAMES = sorted(
    ["Housing", "Utilities", "Food", "Transportation", "Medical & Healthcare", "DayCare", "Church"]
)


# ── helpers ────────────────────────────────────────────────────────


async def _setup(client: AsyncClient):
    """Register a user and return (token, categories, subcategories)."""
    data = await register_user(client)
    token = data["token"]
    headers = auth_header(token)

    cats = (await client.get(f"{BASE}/categories", headers=headers)).json()
    subs = (await client.get(f"{BASE}/subcategories", headers=headers)).json()
    return token, cats, subs


def _find_cat(cats: list[dict], name: str) -> dict:
    return next(c for c in cats if c["name"] == name)


def _find_sub(subs: list[dict], name: str) -> dict:
    return next(s for s in subs if s["name"] == name)


# ── 1. Categories ──────────────────────────────────────────────────


async def test_list_default_categories(client: AsyncClient):
    """Registration seeds exactly 7 default expense categories."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.get(f"{BASE}/categories", headers=headers)
    assert resp.status_code == 200

    cats = resp.json()
    assert len(cats) == 7

    names = sorted(c["name"] for c in cats)
    assert names == DEFAULT_CATEGORY_NAMES

    # All default categories are expense type
    for c in cats:
        assert c["type"] == "expense"
        assert c["is_active"] is True


async def test_create_category(client: AsyncClient):
    """Superadmin can create a new category."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.post(
        f"{BASE}/categories",
        headers=headers,
        json={"type": "savings", "name": "Emergency Fund", "description": "Rainy day"},
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["name"] == "Emergency Fund"
    assert body["type"] == "savings"
    assert body["description"] == "Rainy day"
    assert body["is_active"] is True

    # Verify it shows up in the list
    all_cats = (await client.get(f"{BASE}/categories", headers=headers)).json()
    assert len(all_cats) == 8  # 7 default + 1 new

    # Filter by type
    savings = (
        await client.get(
            f"{BASE}/categories",
            headers=headers,
            params={"type": "savings"},
        )
    ).json()
    assert len(savings) == 1
    assert savings[0]["name"] == "Emergency Fund"


# ── 2. Sub-categories ─────────────────────────────────────────────


async def test_list_subcategories(client: AsyncClient):
    """Registration seeds default subcategories under each category."""
    _token, cats, subs = await _setup(client)

    # Total default subcategories:
    # Housing(5) + Utilities(3) + Food(3) + Transportation(1) +
    # Medical(2) + DayCare(1) + Church(1) = 16
    assert len(subs) == 16

    # Verify a few specific ones
    housing_cat = _find_cat(cats, "Housing")
    housing_subs = [s for s in subs if s["category_id"] == housing_cat["id"]]
    assert sorted(s["name"] for s in housing_subs) == sorted(["ADU", "Home Improvement", "Movie", "Camping", "Hair"])


async def test_list_subcategories_filtered(client: AsyncClient):
    """Filter subcategories by category_id."""
    token, cats, _ = await _setup(client)
    headers = auth_header(token)

    food_cat = _find_cat(cats, "Food")
    resp = await client.get(
        f"{BASE}/subcategories",
        headers=headers,
        params={"category_id": food_cat["id"]},
    )
    assert resp.status_code == 200

    food_subs = resp.json()
    assert len(food_subs) == 3
    assert sorted(s["name"] for s in food_subs) == sorted(["Restaurant", "Grocery", "Indian Grocery"])
    # Each subcategory response should include the parent category
    for s in food_subs:
        assert s["category"]["name"] == "Food"


async def test_create_subcategory(client: AsyncClient):
    """Create a new subcategory under an existing category."""
    token, cats, _ = await _setup(client)
    headers = auth_header(token)

    transport_cat = _find_cat(cats, "Transportation")

    resp = await client.post(
        f"{BASE}/subcategories",
        headers=headers,
        json={
            "category_id": transport_cat["id"],
            "name": "Parking",
            "description": "Parking fees",
        },
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["name"] == "Parking"
    assert body["description"] == "Parking fees"
    assert body["category_id"] == transport_cat["id"]
    assert body["category"]["name"] == "Transportation"

    # Subcategory count should increase
    all_subs = (await client.get(f"{BASE}/subcategories", headers=headers)).json()
    assert len(all_subs) == 17  # 16 default + 1 new


# ── 3. Budgets ─────────────────────────────────────────────────────


async def test_create_budget_monthly(client: AsyncClient):
    """Create a monthly budget for a category."""
    token, cats, _ = await _setup(client)
    headers = auth_header(token)

    housing_cat = _find_cat(cats, "Housing")

    resp = await client.post(
        f"{BASE}/budgets",
        headers=headers,
        json={
            "category_id": housing_cat["id"],
            "period": "monthly",
            "year": 2025,
            "month": 6,
            "amount": 2500.00,
        },
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["period"] == "monthly"
    assert body["year"] == 2025
    assert body["month"] == 6
    assert body["amount"] == 2500.00
    assert body["category_id"] == housing_cat["id"]
    assert body["category"]["name"] == "Housing"
    assert body["is_active"] is True

    # Verify it appears in the list
    budgets = (
        await client.get(
            f"{BASE}/budgets",
            headers=headers,
            params={"year": 2025, "month": 6},
        )
    ).json()
    assert len(budgets) == 1
    assert budgets[0]["id"] == body["id"]


async def test_create_budget_yearly(client: AsyncClient):
    """Create a yearly budget (month should be None)."""
    token, cats, _ = await _setup(client)
    headers = auth_header(token)

    food_cat = _find_cat(cats, "Food")

    resp = await client.post(
        f"{BASE}/budgets",
        headers=headers,
        json={
            "category_id": food_cat["id"],
            "period": "yearly",
            "year": 2025,
            "amount": 12000.00,
        },
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["period"] == "yearly"
    assert body["year"] == 2025
    assert body["month"] is None
    assert body["amount"] == 12000.00


async def test_create_budget_monthly_missing_month(client: AsyncClient):
    """Monthly budget without month should be rejected."""
    token, cats, _ = await _setup(client)
    headers = auth_header(token)

    cat = cats[0]
    resp = await client.post(
        f"{BASE}/budgets",
        headers=headers,
        json={
            "category_id": cat["id"],
            "period": "monthly",
            "year": 2025,
            "amount": 500.00,
        },
    )
    assert resp.status_code == 400


# ── 4. Budget Expenses ─────────────────────────────────────────────


async def test_create_budget_expense(client: AsyncClient):
    """Create a budget expense transaction."""
    token, cats, subs = await _setup(client)
    headers = auth_header(token)

    food_cat = _find_cat(cats, "Food")
    restaurant_sub = _find_sub(subs, "Restaurant")

    resp = await client.post(
        f"{BASE}/expenses",
        headers=headers,
        json={
            "category_id": food_cat["id"],
            "sub_category_id": restaurant_sub["id"],
            "title": "Dinner at Olive Garden",
            "amount": 45.50,
            "currency": "USD",
            "date": "2025-06-15",
            "merchant": "Olive Garden",
            "description": "Family dinner",
            "notes": "Birthday celebration",
        },
    )
    assert resp.status_code == 201

    body = resp.json()
    assert body["title"] == "Dinner at Olive Garden"
    assert body["amount"] == 45.50
    assert body["currency"] == "USD"
    assert body["merchant"] == "Olive Garden"
    assert body["description"] == "Family dinner"
    assert body["notes"] == "Birthday celebration"
    assert body["category"]["name"] == "Food"
    assert body["sub_category"]["name"] == "Restaurant"


async def test_create_expense_wrong_subcategory(client: AsyncClient):
    """Subcategory must belong to the specified category."""
    token, cats, subs = await _setup(client)
    headers = auth_header(token)

    food_cat = _find_cat(cats, "Food")
    # Pick a subcategory from a different category (e.g., Gas -> Transportation)
    gas_sub = _find_sub(subs, "Gas")

    resp = await client.post(
        f"{BASE}/expenses",
        headers=headers,
        json={
            "category_id": food_cat["id"],
            "sub_category_id": gas_sub["id"],
            "title": "Wrong pairing",
            "amount": 10.00,
            "date": "2025-06-15",
        },
    )
    assert resp.status_code == 400


async def test_list_budget_expenses_filtered(client: AsyncClient):
    """Filter expenses by year, month, and category_id."""
    token, cats, subs = await _setup(client)
    headers = auth_header(token)

    food_cat = _find_cat(cats, "Food")
    grocery_sub = _find_sub(subs, "Grocery")
    housing_cat = _find_cat(cats, "Housing")
    adu_sub = _find_sub(subs, "ADU")

    # Create 3 expenses: 2 food in June 2025, 1 housing in July 2025
    for title, cat_id, sub_id, date in [
        ("Groceries week 1", food_cat["id"], grocery_sub["id"], "2025-06-05"),
        ("Groceries week 2", food_cat["id"], grocery_sub["id"], "2025-06-12"),
        ("ADU repair", housing_cat["id"], adu_sub["id"], "2025-07-01"),
    ]:
        resp = await client.post(
            f"{BASE}/expenses",
            headers=headers,
            json={
                "category_id": cat_id,
                "sub_category_id": sub_id,
                "title": title,
                "amount": 100.00,
                "date": date,
            },
        )
        assert resp.status_code == 201

    # All expenses
    all_expenses = (await client.get(f"{BASE}/expenses", headers=headers)).json()
    assert len(all_expenses) == 3

    # Filter by year + month
    june = (
        await client.get(
            f"{BASE}/expenses",
            headers=headers,
            params={"year": 2025, "month": 6},
        )
    ).json()
    assert len(june) == 2

    july = (
        await client.get(
            f"{BASE}/expenses",
            headers=headers,
            params={"year": 2025, "month": 7},
        )
    ).json()
    assert len(july) == 1
    assert july[0]["title"] == "ADU repair"

    # Filter by category_id
    food_expenses = (
        await client.get(
            f"{BASE}/expenses",
            headers=headers,
            params={"category_id": food_cat["id"]},
        )
    ).json()
    assert len(food_expenses) == 2
    assert all(e["category_id"] == food_cat["id"] for e in food_expenses)


# ── 5. Monthly Summary ────────────────────────────────────────────


async def test_monthly_summary(client: AsyncClient):
    """Create multiple expenses and verify the monthly summary."""
    token, cats, subs = await _setup(client)
    headers = auth_header(token)

    food_cat = _find_cat(cats, "Food")
    restaurant_sub = _find_sub(subs, "Restaurant")
    grocery_sub = _find_sub(subs, "Grocery")
    housing_cat = _find_cat(cats, "Housing")
    adu_sub = _find_sub(subs, "ADU")

    # Create expenses in June 2025
    expenses = [
        ("Dinner", food_cat["id"], restaurant_sub["id"], 50.00, "2025-06-10"),
        ("Weekly shop", food_cat["id"], grocery_sub["id"], 120.00, "2025-06-12"),
        ("ADU work", housing_cat["id"], adu_sub["id"], 300.00, "2025-06-15"),
    ]
    for title, cat_id, sub_id, amount, date in expenses:
        resp = await client.post(
            f"{BASE}/expenses",
            headers=headers,
            json={
                "category_id": cat_id,
                "sub_category_id": sub_id,
                "title": title,
                "amount": amount,
                "date": date,
            },
        )
        assert resp.status_code == 201

    # Get summary for June 2025
    resp = await client.get(
        f"{BASE}/summary/monthly",
        headers=headers,
        params={"year": 2025, "month": 6},
    )
    assert resp.status_code == 200

    summary = resp.json()
    assert summary["year"] == 2025
    assert summary["month"] == 6
    assert summary["total_spent"] == pytest.approx(470.00)  # 50 + 120 + 300

    # by_category should have 2 entries (Food and Housing)
    by_cat = {c["category_name"]: c["total_amount"] for c in summary["by_category"]}
    assert len(by_cat) == 2
    assert by_cat["Food"] == pytest.approx(170.00)  # 50 + 120
    assert by_cat["Housing"] == pytest.approx(300.00)

    # by_subcategory should have 3 entries
    by_sub = {s["sub_category_name"]: s["total_amount"] for s in summary["by_subcategory"]}
    assert len(by_sub) == 3
    assert by_sub["Restaurant"] == pytest.approx(50.00)
    assert by_sub["Grocery"] == pytest.approx(120.00)
    assert by_sub["ADU"] == pytest.approx(300.00)


async def test_monthly_summary_empty_month(client: AsyncClient):
    """Summary for a month with no expenses returns zero totals."""
    data = await register_user(client)
    headers = auth_header(data["token"])

    resp = await client.get(
        f"{BASE}/summary/monthly",
        headers=headers,
        params={"year": 2025, "month": 1},
    )
    assert resp.status_code == 200

    summary = resp.json()
    assert summary["total_spent"] == 0
    assert summary["by_category"] == []
    assert summary["by_subcategory"] == []
