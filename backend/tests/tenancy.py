"""Cross-tenant test registry.

Each `OwnedCase` creates a resource as user A and lists the requests user B must not be able
to use against it (each must return 404 and leak no data). Sections add cases as endpoints
are introduced; `tests/integration/test_tenancy.py` sweeps them all.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from tests.helpers import AuthedUser

PUBLIC_ENDPOINTS: set[tuple[str, str]] = {
    ("POST", "/api/v1/auth/register"),
    ("POST", "/api/v1/auth/login"),
    ("POST", "/api/v1/auth/refresh"),
    ("POST", "/api/v1/auth/password-reset/request"),
    ("POST", "/api/v1/auth/password-reset/confirm"),
}


@dataclass(frozen=True)
class Probe:
    method: str
    path: str  # may contain "{id}"
    json: dict[str, Any] | None = None
    files: dict[str, Any] | None = None


@dataclass(frozen=True)
class OwnedCase:
    name: str
    create: Callable[[AuthedUser], str]  # returns the resource id
    probes: list[Probe] = field(default_factory=list)
    # Optional: a list endpoint whose results must not include A's resource when B calls it.
    list_path: str | None = None


OWNED_CASES: list[OwnedCase] = []


def register_case(case: OwnedCase) -> OwnedCase:
    OWNED_CASES.append(case)
    return case
