from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
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
    password: Mapped[str | None] = mapped_column(String, nullable=True, default="")
    google_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String, default="")
    avatar: Mapped[str | None] = mapped_column(String, default="")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class Family(TimestampMixin, Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)

    owner: Mapped[User] = relationship(foreign_keys=[owner_user_id])
    members: Mapped[list[FamilyMembership]] = relationship(back_populates="family")


class FamilyMembership(TimestampMixin, Base):
    __tablename__ = "family_memberships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role: Mapped[FamilyRole] = mapped_column(Enum(FamilyRole), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")

    family: Mapped[Family] = relationship(back_populates="members")
    user: Mapped[User] = relationship()


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    type: Mapped[CategoryType] = mapped_column(Enum(CategoryType), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped[Family] = relationship()
    sub_categories: Mapped[list[SubCategory]] = relationship(back_populates="category")


class SubCategory(TimestampMixin, Base):
    __tablename__ = "sub_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped[Family] = relationship()
    category: Mapped[Category] = relationship(back_populates="sub_categories")


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), index=True)
    sub_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sub_categories.id"), index=True)
    period: Mapped[BudgetPeriod] = mapped_column(Enum(BudgetPeriod), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    month: Mapped[int | None] = mapped_column(Integer, index=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    family: Mapped[Family] = relationship()
    category: Mapped[Category | None] = relationship()
    sub_category: Mapped[SubCategory | None] = relationship()


class BudgetExpense(TimestampMixin, Base):
    __tablename__ = "budget_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    sub_category_id: Mapped[int] = mapped_column(Integer, ForeignKey("sub_categories.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, default="")
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    merchant: Mapped[str | None] = mapped_column(String, default="")
    notes: Mapped[str | None] = mapped_column(Text, default="")

    family: Mapped[Family] = relationship()
    category: Mapped[Category] = relationship()
    sub_category: Mapped[SubCategory] = relationship()


class InvestmentHolding(TimestampMixin, Base):
    __tablename__ = "investment_holdings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
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
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    family: Mapped[Family] = relationship()


class RecurringTransaction(TimestampMixin, Base):
    __tablename__ = "recurring_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    merchant: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="USD")
    frequency: Mapped[RecurringFrequency] = mapped_column(Enum(RecurringFrequency), nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id"), index=True)
    sub_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sub_categories.id"), index=True)
    next_due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    auto_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    notes: Mapped[str | None] = mapped_column(Text, default="")

    family: Mapped[Family] = relationship()
    category: Mapped[Category | None] = relationship()
    sub_category: Mapped[SubCategory | None] = relationship()


class AutoCategoryRule(TimestampMixin, Base):
    __tablename__ = "auto_category_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    merchant_pattern: Mapped[str] = mapped_column(String, nullable=False)
    min_amount: Mapped[float | None] = mapped_column(Float)
    max_amount: Mapped[float | None] = mapped_column(Float)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=False, index=True)
    sub_category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("sub_categories.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    family: Mapped[Family] = relationship()
    category: Mapped[Category] = relationship()
    sub_category: Mapped[SubCategory | None] = relationship()
