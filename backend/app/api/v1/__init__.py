"""Version 1 API router; domain routers are included here."""

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    assets,
    attachments,
    auth,
    budgets,
    categories,
    dashboard,
    goals,
    imports,
    income,
    loans,
    net_worth,
    reports,
    transactions,
    users,
)

api_router = APIRouter(prefix="/api/v1")
for module in (
    auth,
    users,
    accounts,
    assets,
    budgets,
    categories,
    goals,
    transactions,
    attachments,
    imports,
    income,
    loans,
    net_worth,
    reports,
    dashboard,
):
    api_router.include_router(module.router)
