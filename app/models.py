from __future__ import annotations

import enum
from datetime import datetime, date
from typing import Optional, List

from sqlalchemy import (
    String, Float, Integer, Boolean, DateTime, Date, Text,
    ForeignKey, Enum, func, BigInteger,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── Enums ──────────────────────────────────────────────────────────

class CategoryType(str, enum.Enum):
    expense = "expense"
    savings = "savings"


class BudgetPeriod(str, enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class AccountType(str, enum.Enum):
    checking = "checking"
    savings = "savings"
    credit_card = "credit_card"
    investment = "investment"
    loan = "loan"
    mortgage = "mortgage"
    real_estate = "real_estate"
    other = "other"


class AccountOwnership(str, enum.Enum):
    yours = "yours"
    mine = "mine"
    ours = "ours"


class InvestmentType(str, enum.Enum):
    stock = "stock"
    bond = "bond"
    etf = "etf"
    mutual_fund = "mutual_fund"
    crypto = "crypto"
    cash = "cash"
    other = "other"


class RecurringFrequency(str, enum.Enum):
    weekly = "weekly"
    biweekly = "biweekly"
    monthly = "monthly"
    quarterly = "quarterly"
    yearly = "yearly"


class FamilyRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    member = "member"


# ── Mixin ──────────────────────────────────────────────────────────

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


# ── Models ─────────────────────────────────────────────────────────

class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String, default="")
    avatar: Mapped[Optional[str]] = mapped_column(String, default="")

    groups: Mapped[List["Group"]] = relationship(secondary="group_members", back_populates="members")
    expenses: Mapped[List["Expense"]] = relationship(foreign_keys="Expense.payer_id", back_populates="payer")
    splits: Mapped[List["Split"]] = relationship(foreign_keys="Split.user_id", back_populates="user")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Family(TimestampMixin, Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    owner: Mapped["User"] = relationship(foreign_keys=[owner_user_id])
    members: Mapped[List["FamilyMembership"]] = relationship(back_populates="family")


class FamilyMembership(TimestampMixin, Base):
    __tablename__ = "family_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[FamilyRole] = mapped_column(Enum(FamilyRole), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    family: Mapped["Family"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship()


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    type: Mapped[CategoryType] = mapped_column(Enum(CategoryType), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped["Family"] = relationship()
    sub_categories: Mapped[List["SubCategory"]] = relationship(back_populates="category")


class SubCategory(TimestampMixin, Base):
    __tablename__ = "sub_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped["Family"] = relationship()
    category: Mapped["Category"] = relationship(back_populates="sub_categories")


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), index=True)
    sub_category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sub_categories.id"), index=True)
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped["Family"] = relationship()
    category: Mapped[Optional["Category"]] = relationship()
    sub_category: Mapped[Optional["SubCategory"]] = relationship()


class BudgetExpense(TimestampMixin, Base):
    __tablename__ = "budget_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    sub_category_id: Mapped[int] = mapped_column(Integer, ForeignKey("sub_categories.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    merchant: Mapped[Optional[str]] = mapped_column(String, default="")
    notes: Mapped[Optional[str]] = mapped_column(Text, default="")

    family: Mapped["Family"] = relationship()
    category: Mapped["Category"] = relationship()
    sub_category: Mapped["SubCategory"] = relationship()


class Group(TimestampMixin, Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    avatar: Mapped[Optional[str]] = mapped_column(String, default="")
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    members: Mapped[List["User"]] = relationship(secondary="group_members", back_populates="groups")
    expenses: Mapped[List["Expense"]] = relationship(back_populates="group")
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class GroupMember(Base):
    __tablename__ = "group_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="USD")
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    payer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    group_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("groups.id"))
    category: Mapped[Optional[str]] = mapped_column(String, default="")
    receipt: Mapped[Optional[str]] = mapped_column(String, default="")

    payer: Mapped["User"] = relationship(foreign_keys=[payer_id], back_populates="expenses")
    group: Mapped[Optional["Group"]] = relationship(back_populates="expenses")
    splits: Mapped[List["Split"]] = relationship(back_populates="expense")


class Split(TimestampMixin, Base):
    __tablename__ = "splits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expense_id: Mapped[int] = mapped_column(Integer, ForeignKey("expenses.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    percentage: Mapped[Optional[float]] = mapped_column(Float, default=0)

    expense: Mapped["Expense"] = relationship(back_populates="splits")
    user: Mapped["User"] = relationship(foreign_keys=[user_id], back_populates="splits")


class Settlement(TimestampMixin, Base):
    __tablename__ = "settlements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="USD")
    status: Mapped[str] = mapped_column(String, default="pending")
    payment_method: Mapped[Optional[str]] = mapped_column(String, default="")
    notes: Mapped[Optional[str]] = mapped_column(Text, default="")

    from_user: Mapped["User"] = relationship(foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship(foreign_keys=[to_user_id])


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    institution_name: Mapped[str] = mapped_column(String, nullable=False)
    account_name: Mapped[str] = mapped_column(String, nullable=False)
    account_type: Mapped[AccountType] = mapped_column(Enum(AccountType), nullable=False)
    ownership: Mapped[AccountOwnership] = mapped_column(Enum(AccountOwnership), nullable=False, default=AccountOwnership.ours)
    balance: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    is_asset: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    family: Mapped["Family"] = relationship()


class InvestmentHolding(TimestampMixin, Base):
    __tablename__ = "investment_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False, index=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    investment_type: Mapped[InvestmentType] = mapped_column(Enum(InvestmentType), nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cost_basis: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    current_price: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    current_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    gain_loss: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    gain_loss_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    account: Mapped["Account"] = relationship()
    family: Mapped["Family"] = relationship()


class NetWorthSnapshot(TimestampMixin, Base):
    __tablename__ = "net_worth_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    total_assets: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    total_liabilities: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    net_worth: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    family: Mapped["Family"] = relationship()


class RecurringTransaction(TimestampMixin, Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    frequency: Mapped[RecurringFrequency] = mapped_column(Enum(RecurringFrequency), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.id"), index=True)
    sub_category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sub_categories.id"), index=True)
    next_due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, default="")

    family: Mapped["Family"] = relationship()
    category: Mapped[Optional["Category"]] = relationship()
    sub_category: Mapped[Optional["SubCategory"]] = relationship()


class AutoCategoryRule(TimestampMixin, Base):
    __tablename__ = "auto_category_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    merchant_pattern: Mapped[str] = mapped_column(String, nullable=False)
    min_amount: Mapped[Optional[float]] = mapped_column(Float)
    max_amount: Mapped[Optional[float]] = mapped_column(Float)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    sub_category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("sub_categories.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    family: Mapped["Family"] = relationship()
    category: Mapped["Category"] = relationship()
    sub_category: Mapped[Optional["SubCategory"]] = relationship()


class Receipt(TimestampMixin, Base):
    __tablename__ = "receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    budget_expense_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("budget_expenses.id"), index=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str] = mapped_column(String, nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(BigInteger, default=0)
    mime_type: Mapped[Optional[str]] = mapped_column(String, default="")
    merchant: Mapped[Optional[str]] = mapped_column(String, default="")
    amount: Mapped[Optional[float]] = mapped_column(Float)
    date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    notes: Mapped[Optional[str]] = mapped_column(Text, default="")

    family: Mapped["Family"] = relationship()
    budget_expense: Mapped[Optional["BudgetExpense"]] = relationship()
