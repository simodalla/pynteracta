# SPDX-License-Identifier: Apache-2.0
"""Structured logging helpers and redaction utilities.

The library never calls ``structlog.configure()`` at import time.
Call :func:`setup_default_logging` explicitly from a CLI entry-point or test
harness when you want opinionated defaults wired up.
"""

from __future__ import annotations

import logging
import re
import sys
from collections.abc import Mapping, MutableMapping
from typing import Any

import structlog

_REDACTED = "***REDACTED***"

# Matches the leading two Base64-encoded JSON header segments of a JWT.
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9+/._\-]{10,}")

# Body fields whose *key* (case-insensitive) should always be redacted.
_SENSITIVE_KEY_RE = re.compile(r"(?i)token|password|secret|privatekey")


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
    """Shallow-redact sensitive keys in a dict body; returns non-dicts unchanged."""
    if not isinstance(body, dict):
        return body
    return {k: _REDACTED if _SENSITIVE_KEY_RE.search(k) else v for k, v in body.items()}


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
# Opt-in setup helper
# ---------------------------------------------------------------------------


def setup_default_logging(
    level: str = "INFO",
    *,
    json: bool | None = None,
) -> None:
    """Configure structlog with opinionated defaults.

    This is an opt-in helper; the library never calls it implicitly.

    Args:
        level: Log level string (``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``).
        json: Force JSON output when ``True``, console output when ``False``.
            Defaults to ``True`` when stdout is not a TTY.
    """
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
