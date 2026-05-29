# SPDX-License-Identifier: Apache-2.0
"""Base class for resource API clients."""

from __future__ import annotations

from typing import Any

from pynteracta.transport import HttpTransport


class ResourceClient:
    """Base for endpoint-specific clients backed by :class:`~pynteracta.transport.HttpTransport`."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._transport.request("GET", path, params=params)
        body: Any = response.json()
        if not isinstance(body, dict):
            msg = f"Expected JSON object response from {path}"
            raise TypeError(msg)
        return body

    def _post(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        response = self._transport.request("POST", path, json=json, params=params)
        body: Any = response.json()
        if not isinstance(body, dict):
            msg = f"Expected JSON object response from {path}"
            raise TypeError(msg)
        return body
