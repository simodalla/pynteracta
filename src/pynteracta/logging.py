# SPDX-License-Identifier: Apache-2.0
"""Structured logging helpers and redaction utilities.

The library never calls ``structlog.configure()`` at import time.
Call :func:`setup_default_logging` explicitly from a CLI entry-point or test
harness when you want opinionated defaults wired up.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
import sys
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

import structlog

_REDACTED = "***REDACTED***"

# Matches the leading two Base64-encoded JSON header segments of a JWT.
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9+/._\-]{10,}")

# Body fields whose *key* (case-insensitive) should always be redacted.
_SENSITIVE_KEY_RE = re.compile(r"(?i)token|password|secret|privatekey|assertion|jwt")

_AUDIT_LOGGER_NAME = "pynteracta.audit"
_AUDIT_RAW_WARNED = False


# ---------------------------------------------------------------------------
# Public redaction helpers (used by transport.py and tests)
# ---------------------------------------------------------------------------


def redact_string(value: str) -> str:
    """Replace any JWT-shaped substring with ``***REDACTED***``."""
    return _JWT_RE.sub(_REDACTED, value)


def redact_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Return a copy of *headers* with the Authorization value blanked out.

    Any remaining header value that contains a JWT-shaped token is also
    redacted via :func:`redact_string`.
    """
    result: dict[str, str] = {}
    for k, v in headers.items():
        if k.lower() == "authorization":
            result[k] = _REDACTED
        else:
            result[k] = redact_string(v)
    return result


def redact_body(body: Any) -> Any:
    """Recursively redact sensitive keys in a body; returns non-dicts/lists unchanged.

    Walks nested ``dict`` and ``list`` structures, redacting any value whose key
    matches the sensitive-key pattern and applying JWT scrubbing to leaf strings.
    """
    if isinstance(body, dict):
        return {
            k: _REDACTED if _SENSITIVE_KEY_RE.search(k) else redact_body(v) for k, v in body.items()
        }
    if isinstance(body, list):
        return [redact_body(item) for item in body]
    if isinstance(body, str):
        return redact_string(body)
    return body


# ---------------------------------------------------------------------------
# structlog processor
# ---------------------------------------------------------------------------


def redaction_processor(
    logger: Any,
    method: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """structlog processor — redact JWTs and Authorization from every log event.

    Safe to include in the processor chain even when no sensitive data is
    present; it is a no-op for values that do not match.
    """
    _ = logger  # unused but required by the structlog processor signature
    _ = method  # unused but required by the structlog processor signature
    for key in list(event_dict.keys()):
        value = event_dict[key]
        if key == "headers" and isinstance(value, Mapping):
            event_dict[key] = redact_headers(dict(value))
        elif key == "body":
            event_dict[key] = redact_body(value)
        elif isinstance(value, str):
            if key.lower() == "authorization":
                event_dict[key] = _REDACTED
            else:
                event_dict[key] = redact_string(value)
    return event_dict


# ---------------------------------------------------------------------------
# Logger factory
# ---------------------------------------------------------------------------


def get_logger(name: str = "pynteracta") -> Any:
    """Return a named structlog logger."""
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Audit file handler builder
# ---------------------------------------------------------------------------


def build_audit_file_handler(
    path: Path,
    *,
    max_bytes: int = 10_000_000,
    backup_count: int = 5,
) -> logging.Handler:
    """Return a :class:`~logging.handlers.RotatingFileHandler` for JSON-lines audit output.

    The handler uses the same structlog redaction processor chain so tokens are
    never written to disk in clear text.
    """
    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.EventRenamer("event"),
        redaction_processor,
    ]
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(formatter)
    return handler


# ---------------------------------------------------------------------------
# Opt-in setup helper
# ---------------------------------------------------------------------------


def setup_default_logging(  # noqa: PLR0913
    level: str = "INFO",
    *,
    json: bool | None = None,
    audit: bool = False,
    audit_file: Path | None = None,
    audit_max_bytes: int = 10_000_000,
    audit_backups: int = 5,
    audit_bodies: bool = False,
    audit_raw: bool = False,
) -> None:
    """Configure structlog with opinionated defaults.

    This is an opt-in helper; the library never calls it implicitly.

    Args:
        level: Log level string (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
        json: Force JSON output when ``True``, console output when ``False``.
            Defaults to ``True`` when stdout is not a TTY.
        audit: Enable the dedicated ``pynteracta.audit`` logger.
        audit_file: If set, attach a :class:`~logging.handlers.RotatingFileHandler`
            writing JSON-lines to this path.  Implies ``audit=True``.
        audit_max_bytes: Max bytes per audit log file before rotation (default 10 MB).
        audit_backups: Number of rotated backup files to keep (default 5).
        audit_bodies: Whether audit events should include request/response bodies.
            Bodies are **never** captured unless this is ``True``.
        audit_raw: If ``True``, bypass redaction on the audit channel and emit a
            loud warning.  Use only for deep debugging; never in production.
    """
    global _AUDIT_RAW_WARNED  # noqa: PLW0603

    use_json = json if json is not None else not sys.stdout.isatty()

    shared_processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.EventRenamer("event"),
        redaction_processor,
    ]

    if use_json:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[*shared_processors, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger("pynteracta")
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # ------------------------------------------------------------------
    # Audit logger
    # ------------------------------------------------------------------
    enable_audit = audit or audit_file is not None
    if enable_audit:
        audit_logger = logging.getLogger(_AUDIT_LOGGER_NAME)
        audit_logger.setLevel(logging.DEBUG)
        audit_logger.propagate = False  # don't double-emit on root pynteracta logger

        if audit_raw and not _AUDIT_RAW_WARNED:
            _AUDIT_RAW_WARNED = True
            audit_processors_raw: list[Any] = [
                structlog.stdlib.add_log_level,
                structlog.stdlib.add_logger_name,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.EventRenamer("event"),
                # redaction_processor intentionally omitted
            ]
            raw_formatter = structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=audit_processors_raw,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    structlog.processors.JSONRenderer(),
                ],
            )
            raw_console_handler = logging.StreamHandler()
            raw_console_handler.setFormatter(raw_formatter)
            audit_logger.addHandler(raw_console_handler)
            logging.getLogger("pynteracta").warning(
                "audit.redaction_disabled: --audit-raw is active — "
                "raw tokens and sensitive data MAY appear in audit output. "
                "Never use this in production."
            )
        else:
            audit_console_handler = logging.StreamHandler()
            audit_console_formatter = structlog.stdlib.ProcessorFormatter(
                foreign_pre_chain=shared_processors,
                processors=[
                    structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                    renderer,
                ],
            )
            audit_console_handler.setFormatter(audit_console_formatter)
            audit_logger.addHandler(audit_console_handler)

        if audit_file is not None:
            file_handler = build_audit_file_handler(
                audit_file,
                max_bytes=audit_max_bytes,
                backup_count=audit_backups,
            )
            if audit_raw:
                # Apply raw (no-redaction) formatter to file handler too
                raw_file_processors: list[Any] = [
                    structlog.stdlib.add_log_level,
                    structlog.stdlib.add_logger_name,
                    structlog.processors.TimeStamper(fmt="iso", utc=True),
                    structlog.processors.EventRenamer("event"),
                ]
                raw_file_formatter = structlog.stdlib.ProcessorFormatter(
                    foreign_pre_chain=raw_file_processors,
                    processors=[
                        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                        structlog.processors.JSONRenderer(),
                    ],
                )
                file_handler.setFormatter(raw_file_formatter)
            audit_logger.addHandler(file_handler)
