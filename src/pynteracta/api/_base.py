# SPDX-License-Identifier: Apache-2.0
"""Base class for resource API clients."""

from __future__ import annotations

from typing import Any

from pynteracta.exceptions import NotFoundError
from pynteracta.transport import HttpTransport

_HTTP_NO_CONTENT = 204


class ResourceClient:
    """Base for endpoint-specific clients backed by :class:`~pynteracta.transport.HttpTransport`."""

    def __init__(self, transport: HttpTransport) -> None:
        self._transport = transport

    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Una ``GET``; un ``204`` senza corpo è ``NotFoundError`` (05-C27).

        È la risposta del tenant al form di un utente inesistente: non c'è JSON da leggere e la
        risorsa non c'è. L'errore non passa dal transport, quindi gli hook non lo vedono, come
        per il ``TypeError`` sul corpo che non è un oggetto.
        """
        response = self._transport.request("GET", path, params=params)
        if response.status_code == _HTTP_NO_CONTENT and not response.content:
            msg = f"Empty 204 response from {path}: resource not found"
            raise NotFoundError(
                msg, status_code=_HTTP_NO_CONTENT, request_method="GET", request_url=path
            )
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

    def _put(
        self,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Una ``PUT``; una risposta senza corpo vale come oggetto vuoto (edit-post-watchers)."""
        response = self._transport.request("PUT", path, json=json, params=params)
        if not response.content:
            return {}
        body: Any = response.json()
        if not isinstance(body, dict):
            msg = f"Expected JSON object response from {path}"
            raise TypeError(msg)
        return body

    def _delete(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Una ``DELETE``; una risposta senza corpo vale come oggetto vuoto."""
        response = self._transport.request("DELETE", path, params=params)
        if not response.content:
            return {}
        body: Any = response.json()
        if not isinstance(body, dict):
            msg = f"Expected JSON object response from {path}"
            raise TypeError(msg)
        return body
