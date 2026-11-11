"""Outbound email behind a Protocol (SMTP/Mailpit in dev, in-memory in tests)."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from functools import lru_cache
from typing import Protocol

import structlog

from app.core.config import get_settings

log = structlog.get_logger("app.email")


@dataclass(frozen=True)
class OutgoingEmail:
    to: str
    subject: str
    body: str


class EmailSender(Protocol):
    def send(self, message: OutgoingEmail) -> None: ...


class SmtpEmailSender:
    def __init__(self, host: str, port: int, sender: str) -> None:
        self.host, self.port, self.sender = host, port, sender

    def send(self, message: OutgoingEmail) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = message.to
        msg["Subject"] = message.subject
        msg.set_content(message.body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
                smtp.send_message(msg)
            log.info("email_sent", subject=message.subject)
        except OSError as exc:  # never surface delivery problems to the client
            log.error("email_failed", subject=message.subject, error=type(exc).__name__)


@dataclass
class InMemoryEmailSender:
    outbox: list[OutgoingEmail] = field(default_factory=list)

    def send(self, message: OutgoingEmail) -> None:
        self.outbox.append(message)


@lru_cache
def get_email_sender() -> EmailSender:
    s = get_settings()
    return SmtpEmailSender(s.smtp_host, s.smtp_port, s.smtp_from)
