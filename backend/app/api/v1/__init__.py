"""Version 1 API router; domain routers are included here."""

from fastapi import APIRouter

from app.api.v1 import (
    accounts,
    attachments,
    auth,
    categories,
    dashboard,
    imports,
    income,
    reports,
    transactions,
    users,
)

api_router = APIRouter(prefix="/api/v1")
for module in (
    auth,
    users,
    accounts,
    categories,
    transactions,
    attachments,
    imports,
    income,
    reports,
    dashboard,
):
    api_router.include_router(module.router)
