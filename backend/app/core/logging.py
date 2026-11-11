"""Structured JSON logging with redaction of sensitive keys."""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

REDACTED = "[REDACTED]"
# Any key containing one of these fragments is redacted (case-insensitive).
SENSITIVE_KEY_FRAGMENTS = (
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "amount",
    "balance",
    "description",
    "notes",
    "payee",
    "account_number",
    "last4",
    "reset_link",
    "gross",
    "deduction",
)


def _is_sensitive(key: str) -> bool:
    k = key.lower()
    return any(frag in k for frag in SENSITIVE_KEY_FRAGMENTS)


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: REDACTED if _is_sensitive(str(k)) else _redact(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [_redact(v) for v in value]
    return value


def redact_processor(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    for key in list(event_dict.keys()):
        if key == "event":
            continue
        event_dict[key] = REDACTED if _is_sensitive(key) else _redact(event_dict[key])
    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
