# SPDX-License-Identifier: Apache-2.0
"""Exception hierarchy for pynteracta."""

from __future__ import annotations

from typing import Any


class InteractaError(Exception):
    """Base class for all pynteracta errors."""

    def __init__(  # noqa: PLR0913
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        request_method: str | None = None,
        request_url: str | None = None,
        response_body: Any = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.request_method = request_method
        self.request_url = request_url
        self.response_body = response_body
        self.request_id = request_id


class AuthenticationError(InteractaError):
    """401 or token-build failure."""


class PermissionError(InteractaError):
    """403 -- use builtins.PermissionError for the stdlib one."""


class NotFoundError(InteractaError):
    """404."""


class ValidationError(InteractaError):
    """400 with a validation error payload."""

    def __init__(
        self,
        message: str = "",
        *,
        errors: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(message, **kwargs)
        self.errors: list[dict[str, Any]] = errors or []


class CustomFieldValidationError(ValidationError):
    """400 with a custom-field validation error payload."""


class ConcurrencyError(InteractaError):
    """409 -- placeholder for occToken flows."""


class ServerError(InteractaError):
    """5xx."""


class TransportError(InteractaError):
    """Network failures, timeouts, DNS, TLS."""
