"""Hooks run when a user deletes their account.

A hook runs inside the deletion transaction (before rows cascade away) and may return a
callable to run after commit, e.g. removing stored files.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from sqlalchemy.orm import Session

PostCommit = Callable[[], None]
DeletionHook = Callable[[Session, uuid.UUID], PostCommit | None]
_HOOKS: list[DeletionHook] = []


def on_user_deleted(hook: DeletionHook) -> DeletionHook:
    if hook not in _HOOKS:
        _HOOKS.append(hook)
    return hook


def run_deletion_hooks(db: Session, user_id: uuid.UUID) -> list[PostCommit]:
    after: list[PostCommit] = []
    for hook in _HOOKS:
        action = hook(db, user_id)
        if action is not None:
            after.append(action)
    return after
