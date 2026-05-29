# SPDX-License-Identifier: Apache-2.0
"""HTTP transport layer: httpx wrapper, auth injection, error mapping, logging."""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from typing import Any

import httpx
import structlog

from pynteracta import __version__
from pynteracta.exceptions import (
    AuthenticationError,
    ConcurrencyError,
    CustomFieldValidationError,
    InteractaError,
    NotFoundError,
    ServerError,
    TransportError,
    ValidationError,
)

# Aliased to avoid shadowing the builtin PermissionError in this module.
from pynteracta.exceptions import PermissionError as InteractaPermissionError
from pynteracta.hooks import ClientHooks, RequestInfo, ResponseInfo
from pynteracta.logging import redact_headers, redact_string

_log = structlog.get_logger("pynteracta.transport")

_PY_VERSION = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
_DEFAULT_USER_AGENT = f"pynteracta/{__version__} python/{_PY_VERSION} httpx/{httpx.__version__}"

_HTTP_400 = 400
_HTTP_401 = 401
_HTTP_403 = 403
_HTTP_404 = 404
_HTTP_409 = 409
_HTTP_5XX_LOW = 500
_HTTP_5XX_HIGH = 600


class HttpTransport:
    """Synchronous HTTP transport wrapping ``httpx.Client``.

    Args:
        base_url: Already-built API base URL (e.g. from
            :func:`~pynteracta.urls.build_api_base`).
        token_provider: Callable that returns a valid access token string.
            When ``None``, the ``Authorization`` header is not injected.
        hooks: Observer implementing :class:`~pynteracta.hooks.ClientHooks`.
        timeout: Request timeout in seconds (default 30).
        user_agent: Override the default ``User-Agent`` header.
        auth_scheme: Prefix for the ``Authorization`` value (e.g. ``"Bearer"``).
            ``None`` sends the raw token with no prefix.
    """

    def __init__(  # noqa: PLR0913
        self,
        base_url: str,
        *,
        token_provider: Callable[[], str] | None = None,
        hooks: ClientHooks | None = None,
        timeout: float = 30.0,
        user_agent: str | None = None,
        auth_scheme: str | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._token_provider = token_provider
        self._hooks = hooks
        self._user_agent = user_agent or _DEFAULT_USER_AGENT
        self._auth_scheme = auth_scheme
        self._client = httpx.Client(timeout=timeout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any = None,
    ) -> httpx.Response:
        """Execute a synchronous HTTP request and return the response.

        Raises the appropriate :class:`~pynteracta.exceptions.InteractaError`
        subclass for any non-2xx status or network-level failure.
        """
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = self._build_headers()

        redacted_headers = redact_headers(headers)
        redacted_url = redact_string(url)

        req_info = RequestInfo(method=method, url=redacted_url, headers=redacted_headers)
        _log.debug("http.request", method=method, url=redacted_url)
        if self._hooks is not None:
            self._hooks.on_request(req_info)

        try:
            start = time.perf_counter()
            response = self._client.request(method, url, headers=headers, params=params, json=json)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
        except httpx.TimeoutException as exc:
            _log.warning("http.error", error_type="timeout", message=str(exc))
            err = TransportError(str(exc), request_method=method, request_url=redacted_url)
            if self._hooks is not None:
                self._hooks.on_error(err)
            raise err from exc
        except httpx.NetworkError as exc:
            _log.warning("http.error", error_type="network", message=str(exc))
            err = TransportError(str(exc), request_method=method, request_url=redacted_url)
            if self._hooks is not None:
                self._hooks.on_error(err)
            raise err from exc

        request_id = response.headers.get("x-request-id")
        resp_info = ResponseInfo(
            status_code=response.status_code,
            url=redacted_url,
            headers=dict(response.headers),
            elapsed_ms=elapsed_ms,
            request_id=request_id,
        )
        _log.debug(
            "http.response",
            status=response.status_code,
            duration_ms=round(elapsed_ms, 2),
        )
        if self._hooks is not None:
            self._hooks.on_response(resp_info)

        if response.is_success:
            return response

        mapped = self._map_error(response, redacted_url)
        if self._hooks is not None:
            self._hooks.on_error(mapped)
        raise mapped

    def close(self) -> None:
        """Close the underlying ``httpx.Client``."""
        self._client.close()

    def __enter__(self) -> HttpTransport:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"User-Agent": self._user_agent}
        if self._token_provider is not None:
            token = self._token_provider()
            auth_value = f"{self._auth_scheme} {token}" if self._auth_scheme else token
            headers["Authorization"] = auth_value
        return headers

    def _map_error(  # noqa: PLR0911
        self, response: httpx.Response, redacted_url: str
    ) -> InteractaError:
        status = response.status_code
        method = response.request.method
        request_id = response.headers.get("x-request-id")

        try:
            body: Any = response.json()
        except Exception:
            body = response.text or None

        _log.warning("http.error", status=status, error_type="http_error", message=f"HTTP {status}")

        common: dict[str, Any] = dict(
            status_code=status,
            request_method=method,
            request_url=redacted_url,
            response_body=body,
            request_id=request_id,
        )

        if status == _HTTP_400:
            if isinstance(body, dict) and "customFieldValidationErrors" in body:
                return CustomFieldValidationError("Validation failed", **common)
            if isinstance(body, dict) and "validationErrors" in body:
                errors: list[dict[str, Any]] = body.get("validationErrors") or []
                return ValidationError("Validation failed", errors=errors, **common)
            return ValidationError("Bad request", **common)
        if status == _HTTP_401:
            return AuthenticationError("Unauthorized", **common)
        if status == _HTTP_403:
            return InteractaPermissionError("Forbidden", **common)
        if status == _HTTP_404:
            return NotFoundError("Not found", **common)
        if status == _HTTP_409:
            return ConcurrencyError("Conflict", **common)
        if _HTTP_5XX_LOW <= status < _HTTP_5XX_HIGH:
            return ServerError(f"Server error {status}", **common)
        return InteractaError(f"HTTP {status}", **common)
