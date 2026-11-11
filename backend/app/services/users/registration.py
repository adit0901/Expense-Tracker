"""Hooks run inside the registration transaction (e.g. seeding default categories)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.models.user import User

RegistrationHook = Callable[[Session, User], None]
_HOOKS: list[RegistrationHook] = []


def on_user_registered(hook: RegistrationHook) -> RegistrationHook:
    if hook not in _HOOKS:
        _HOOKS.append(hook)
    return hook


def run_registration_hooks(db: Session, user: User) -> None:
    for hook in _HOOKS:
        hook(db, user)
