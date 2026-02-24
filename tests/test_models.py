"""Unit tests to verify all models import and have correct table names."""
import os
os.environ.setdefault("JWT_SECRET", "test-secret-key")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_PASSWORD", "test")

from app.models import (
    User, Family, FamilyMembership, Category, SubCategory,
    Budget, BudgetExpense, Group, GroupMember, Expense, Split,
    Settlement, Account, InvestmentHolding, NetWorthSnapshot,
    RecurringTransaction, AutoCategoryRule, Receipt,
    CategoryType, BudgetPeriod, AccountType, AccountOwnership,
    InvestmentType, RecurringFrequency, FamilyRole,
)


def test_table_names():
    assert User.__tablename__ == "users"
    assert Family.__tablename__ == "families"
    assert FamilyMembership.__tablename__ == "family_memberships"
    assert Category.__tablename__ == "categories"
    assert SubCategory.__tablename__ == "sub_categories"
    assert Budget.__tablename__ == "budgets"
    assert BudgetExpense.__tablename__ == "budget_expenses"
    assert Group.__tablename__ == "groups"
    assert GroupMember.__tablename__ == "group_members"
    assert Expense.__tablename__ == "expenses"
    assert Split.__tablename__ == "splits"
    assert Settlement.__tablename__ == "settlements"
    assert Account.__tablename__ == "accounts"
    assert InvestmentHolding.__tablename__ == "investment_holdings"
    assert NetWorthSnapshot.__tablename__ == "net_worth_snapshots"
    assert RecurringTransaction.__tablename__ == "recurring_transactions"
    assert AutoCategoryRule.__tablename__ == "auto_category_rules"
    assert Receipt.__tablename__ == "receipts"


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
    """Ensure we have all 18 models."""
    from app.database import Base
    tables = Base.metadata.tables
    assert len(tables) == 18, f"Expected 18 tables, got {len(tables)}: {list(tables.keys())}"
