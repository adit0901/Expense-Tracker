"""Financial planning tables: budgets, goals, assets, loans, net worth.

Revision ID: 0006
Revises: 0005
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Enums
    goal_type = postgresql.ENUM(
        "emergency_fund",
        "vacation",
        "house",
        "vehicle",
        "education",
        "retirement",
        "other",
        name="goal_type",
    )
    goal_type.create(op.get_bind(), checkfirst=True)

    goal_status = postgresql.ENUM(
        "active", "paused", "completed", "archived", name="goal_status"
    )
    goal_status.create(op.get_bind(), checkfirst=True)

    goal_contribution_kind = postgresql.ENUM(
        "contribution", "withdrawal", name="goal_contribution_kind"
    )
    goal_contribution_kind.create(op.get_bind(), checkfirst=True)

    asset_type = postgresql.ENUM(
        "fixed_deposit",
        "gold",
        "real_estate",
        "ppf",
        "epf",
        "nps",
        "mutual_fund",
        "vehicle",
        "other",
        name="asset_type",
    )
    asset_type.create(op.get_bind(), checkfirst=True)

    loan_type = postgresql.ENUM(
        "home", "car", "personal", "education", "other", name="loan_type"
    )
    loan_type.create(op.get_bind(), checkfirst=True)

    loan_status = postgresql.ENUM("active", "closed", name="loan_status")
    loan_status.create(op.get_bind(), checkfirst=True)

    loan_event_kind = postgresql.ENUM(
        "rate_change", "prepayment", "emi_override", name="loan_event_kind"
    )
    loan_event_kind.create(op.get_bind(), checkfirst=True)

    # 2. Budgets
    op.create_table(
        "budgets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("overall_amount", sa.Numeric(19, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("overall_amount IS NULL OR overall_amount > 0", name="budget_overall_positive"),
        sa.UniqueConstraint("user_id", "month", name="uq_budgets_user_month"),
    )

    op.create_table(
        "budget_lines",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("budget_id", sa.UUID(), sa.ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("category_id", sa.UUID(), sa.ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("alert_thresholds", postgresql.ARRAY(sa.Integer()), nullable=False, server_default="{80,100}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="budget_line_amount_positive"),
        sa.UniqueConstraint("budget_id", "category_id", name="uq_budget_lines_budget_category"),
    )

    op.create_table(
        "budget_alerts",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("budget_line_id", sa.UUID(), sa.ForeignKey("budget_lines.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "uq_budget_alerts_line_month_threshold",
        "budget_alerts",
        ["user_id", "budget_line_id", "month", "threshold"],
        unique=True,
        postgresql_nulls_not_distinct=True,
    )

    # 3. Savings targets & Goals
    op.create_table(
        "savings_targets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="savings_target_positive"),
        sa.UniqueConstraint("user_id", "effective_from", name="uq_savings_targets_user_effective"),
    )

    op.create_table(
        "goals",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", postgresql.ENUM(name="goal_type", create_type=False), nullable=False),
        sa.Column("target_amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("starting_amount", sa.Numeric(19, 4), server_default="0", nullable=False),
        sa.Column("status", postgresql.ENUM(name="goal_status", create_type=False), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("target_amount > 0", name="goal_target_positive"),
        sa.CheckConstraint("starting_amount >= 0", name="goal_starting_non_negative"),
    )

    op.create_table(
        "goal_contributions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("goal_id", sa.UUID(), sa.ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", postgresql.ENUM(name="goal_contribution_kind", create_type=False), server_default="contribution", nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("transaction_id", sa.UUID(), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("amount > 0", name="goal_contribution_amount_positive"),
    )
    op.create_index("ix_goal_contributions_goal_date", "goal_contributions", ["goal_id", "date"])

    # 4. Assets & Liabilities
    op.create_table(
        "assets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", postgresql.ENUM(name="asset_type", create_type=False), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("is_liquid", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("closed_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "asset_valuations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("asset_id", sa.UUID(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("value", sa.Numeric(19, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("value >= 0", name="asset_valuation_non_negative"),
        sa.UniqueConstraint("asset_id", "as_of", name="uq_asset_valuations_asset_as_of"),
    )

    op.create_table(
        "liabilities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("closed_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    op.create_table(
        "liability_balances",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("liability_id", sa.UUID(), sa.ForeignKey("liabilities.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("balance", sa.Numeric(19, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("balance >= 0", name="liability_balance_non_negative"),
        sa.UniqueConstraint("liability_id", "as_of", name="uq_liability_balances_liability_as_of"),
    )

    # 5. Loans
    op.create_table(
        "loans",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("type", postgresql.ENUM(name="loan_type", create_type=False), nullable=False),
        sa.Column("lender", sa.String(100), nullable=False),
        sa.Column("original_principal", sa.Numeric(19, 4), nullable=False),
        sa.Column("annual_rate", sa.Numeric(7, 4), nullable=False),
        sa.Column("tenure_months", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("first_emi_date", sa.Date(), nullable=False),
        sa.Column("emi_amount", sa.Numeric(19, 4), nullable=True),
        sa.Column("emi_overridden", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("baseline_outstanding", sa.Numeric(19, 4), nullable=True),
        sa.Column("baseline_date", sa.Date(), nullable=True),
        sa.Column("status", postgresql.ENUM(name="loan_status", create_type=False), server_default="active", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.CheckConstraint("original_principal > 0", name="loan_principal_positive"),
        sa.CheckConstraint("annual_rate >= 0", name="loan_rate_non_negative"),
        sa.CheckConstraint("tenure_months > 0", name="loan_tenure_positive"),
    )

    op.create_table(
        "loan_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("loan_id", sa.UUID(), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("kind", postgresql.ENUM(name="loan_event_kind", create_type=False), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_loan_events_loan_date", "loan_events", ["loan_id", "effective_date"])

    op.create_table(
        "loan_payments",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("loan_id", sa.UUID(), sa.ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("installment_no", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.UUID(), sa.ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("principal", sa.Numeric(19, 4), nullable=False),
        sa.Column("interest", sa.Numeric(19, 4), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # 6. Net worth snapshots
    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("as_of", sa.Date(), nullable=False),
        sa.Column("total_assets", sa.Numeric(19, 4), nullable=False),
        sa.Column("total_liabilities", sa.Numeric(19, 4), nullable=False),
        sa.Column("net_worth", sa.Numeric(19, 4), nullable=False),
        sa.Column("breakdown", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_stale", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "as_of", name="uq_net_worth_snapshots_user_as_of"),
    )

    # 7. Add loan columns to transactions table
    op.add_column("transactions", sa.Column("loan_id", sa.UUID(), sa.ForeignKey("loans.id", ondelete="SET NULL"), nullable=True))
    op.add_column("transactions", sa.Column("principal_component", sa.Numeric(19, 4), nullable=True))
    op.add_column("transactions", sa.Column("interest_component", sa.Numeric(19, 4), nullable=True))
    op.create_check_constraint(
        "loan_payment_components",
        "transactions",
        "type <> 'loan_payment' OR (loan_id IS NOT NULL AND principal_component IS NOT NULL AND interest_component IS NOT NULL AND (principal_component + interest_component) = amount)",
    )
    op.create_check_constraint(
        "loan_components_only_for_loan_payment",
        "transactions",
        "type = 'loan_payment' OR (loan_id IS NULL AND principal_component IS NULL AND interest_component IS NULL)",
    )


def downgrade() -> None:
    op.drop_constraint("loan_components_only_for_loan_payment", "transactions", type_="check")
    op.drop_constraint("loan_payment_components", "transactions", type_="check")
    op.drop_column("transactions", "interest_component")
    op.drop_column("transactions", "principal_component")
    op.drop_column("transactions", "loan_id")

    op.drop_table("net_worth_snapshots")
    op.drop_table("loan_payments")
    op.drop_table("loan_events")
    op.drop_table("loans")
    op.drop_table("liability_balances")
    op.drop_table("liabilities")
    op.drop_table("asset_valuations")
    op.drop_table("assets")
    op.drop_table("goal_contributions")
    op.drop_table("goals")
    op.drop_table("savings_targets")
    op.drop_table("budget_alerts")
    op.drop_table("budget_lines")
    op.drop_table("budgets")

    bind = op.get_bind()
    postgresql.ENUM(name="loan_event_kind").drop(bind, checkfirst=True)
    postgresql.ENUM(name="loan_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="loan_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="asset_type").drop(bind, checkfirst=True)
    postgresql.ENUM(name="goal_contribution_kind").drop(bind, checkfirst=True)
    postgresql.ENUM(name="goal_status").drop(bind, checkfirst=True)
    postgresql.ENUM(name="goal_type").drop(bind, checkfirst=True)

