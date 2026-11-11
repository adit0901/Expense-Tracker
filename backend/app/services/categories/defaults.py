"""Default categories seeded for every new user (transaction-categories spec)."""

from __future__ import annotations

from typing import NamedTuple

from app.models.enums import CategoryKind


class DefaultCategory(NamedTuple):
    kind: CategoryKind
    name: str
    color: str
    icon: str
    is_essential: bool = False
    is_system: bool = False


E, INC = CategoryKind.expense, CategoryKind.income

DEFAULT_CATEGORIES: tuple[DefaultCategory, ...] = (
    DefaultCategory(E, "Food", "#E8590C", "utensils", is_essential=True),
    DefaultCategory(E, "Rent", "#5F3DC4", "home", is_essential=True),
    DefaultCategory(E, "Shopping", "#C2255C", "shopping-bag"),
    DefaultCategory(E, "Travel", "#1971C2", "plane"),
    DefaultCategory(E, "Healthcare", "#2F9E44", "heart-pulse", is_essential=True),
    DefaultCategory(E, "Utilities", "#0C8599", "plug", is_essential=True),
    DefaultCategory(E, "Fuel", "#E67700", "fuel"),
    DefaultCategory(E, "Entertainment", "#9C36B5", "clapperboard"),
    DefaultCategory(E, "Insurance", "#364FC7", "shield", is_essential=True),
    DefaultCategory(E, "Education", "#087F5B", "graduation-cap", is_essential=True),
    DefaultCategory(E, "Loan Interest", "#C92A2A", "landmark", is_essential=True, is_system=True),
    DefaultCategory(E, "Others", "#868E96", "circle-ellipsis"),
    DefaultCategory(INC, "Salary", "#2B8A3E", "briefcase"),
    DefaultCategory(INC, "Bonus", "#5C940D", "gift"),
    DefaultCategory(INC, "Freelance", "#1864AB", "laptop"),
    DefaultCategory(INC, "Business", "#862E9C", "store"),
    DefaultCategory(INC, "Rental", "#A61E4D", "building"),
    DefaultCategory(INC, "Dividends", "#0B7285", "trending-up"),
    DefaultCategory(INC, "Interest", "#5F3DC4", "percent"),
    DefaultCategory(INC, "Other Income", "#868E96", "circle-plus"),
)
