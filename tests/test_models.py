"""Unit tests to verify all models import and have correct table names."""

import os

os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PASSWORD", "test")

from app.models import (
    Account,
    AccountOwnership,
    AccountType,
    AutoCategoryRule,
    Budget,
    BudgetExpense,
    BudgetPeriod,
    Category,
    CategoryType,
    Family,
    FamilyMembership,
    FamilyRole,
    InvestmentHolding,
    InvestmentType,
    NetWorthSnapshot,
    RecurringFrequency,
    RecurringTransaction,
    SubCategory,
    User,
)


def test_table_names():
    assert User.__tablename__ == "users"
    assert Family.__tablename__ == "families"
    assert FamilyMembership.__tablename__ == "family_memberships"
    assert Category.__tablename__ == "categories"
    assert SubCategory.__tablename__ == "sub_categories"
    assert Budget.__tablename__ == "budgets"
    assert BudgetExpense.__tablename__ == "budget_expenses"
    assert Account.__tablename__ == "accounts"
    assert InvestmentHolding.__tablename__ == "investment_holdings"
    assert NetWorthSnapshot.__tablename__ == "net_worth_snapshots"
    assert RecurringTransaction.__tablename__ == "recurring_transactions"
    assert AutoCategoryRule.__tablename__ == "auto_category_rules"


def test_enums():
    assert CategoryType.expense.value == "expense"
    assert CategoryType.savings.value == "savings"
    assert BudgetPeriod.monthly.value == "monthly"
    assert AccountType.checking.value == "checking"
    assert AccountOwnership.ours.value == "ours"
    assert InvestmentType.stock.value == "stock"
    assert RecurringFrequency.monthly.value == "monthly"
    assert FamilyRole.superadmin.value == "superadmin"


def test_model_count():
    """Ensure we have all 12 models."""
    from app.database import Base

    tables = Base.metadata.tables
    assert len(tables) == 12, f"Expected 12 tables, got {len(tables)}: {list(tables.keys())}"
