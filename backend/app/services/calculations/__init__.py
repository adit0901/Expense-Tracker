"""Financial planning calculations package."""

from app.services.calculations.figures import (
    CategoryTotal,
    PeriodFigures,
    category_totals,
    period_figures,
    savings,
    savings_rate,
    total_expenses,
    total_income,
)
from app.services.calculations.loans import (
    Installment,
    LoanBaseline,
    LoanEvent,
    LoanPaymentRecord,
    ScheduleResult,
    SimulationResult,
    build_schedule,
    compute_emi,
    simulate_loan,
)
from app.services.calculations.net_worth import (
    BreakdownItem,
    NetWorthResult,
    compute_growth,
    compute_net_worth_figures,
    default_investment_value_provider,
)
from app.services.calculations.planning import (
    budget_remaining,
    budget_utilization,
    emergency_fund_coverage,
    goal_estimated_completion_date,
    goal_progress_pct,
    goal_remaining,
    goal_required_monthly_contribution,
    savings_target_achievement,
)

__all__ = [
    "BreakdownItem",
    "CategoryTotal",
    "Installment",
    "LoanBaseline",
    "LoanEvent",
    "LoanPaymentRecord",
    "NetWorthResult",
    "PeriodFigures",
    "ScheduleResult",
    "SimulationResult",
    "budget_remaining",
    "budget_utilization",
    "build_schedule",
    "category_totals",
    "compute_emi",
    "compute_growth",
    "compute_net_worth_figures",
    "default_investment_value_provider",
    "emergency_fund_coverage",
    "goal_estimated_completion_date",
    "goal_progress_pct",
    "goal_remaining",
    "goal_required_monthly_contribution",
    "period_figures",
    "savings",
    "savings_rate",
    "savings_target_achievement",
    "simulate_loan",
    "total_expenses",
    "total_income",
]

