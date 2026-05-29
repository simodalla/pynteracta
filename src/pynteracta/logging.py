# SPDX-License-Identifier: Apache-2.0
"""Structured logging helpers.

The library never calls ``structlog.configure()`` at import time.
Call :func:`setup_default_logging` explicitly from a CLI entry-point or test
harness when you want opinionated defaults wired up.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog


def get_logger(name: str = "pynteracta") -> Any:
    """Return a named structlog logger."""
    return structlog.get_logger(name)


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
