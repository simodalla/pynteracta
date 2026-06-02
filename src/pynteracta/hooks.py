# SPDX-License-Identifier: Apache-2.0
"""Framework-agnostic hook types for request/response observation.

No ``httpx`` types appear here; the transport backend stays an implementation
detail and can be swapped without breaking callers.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class RequestInfo:
    """Snapshot of an outgoing HTTP request (after redaction)."""

    method: str
    url: str
    headers: Mapping[str, str]
    body: Any = field(default=None)


@dataclass(frozen=True)
class ResponseInfo:
    """Snapshot of a received HTTP response."""

    status_code: int
    url: str
    headers: Mapping[str, str]
    elapsed_ms: float
    request_id: str | None
    body: Any = field(default=None)


@runtime_checkable
class ClientHooks(Protocol):
    """Observer protocol — implement to intercept request/response events."""

    def on_request(self, req: RequestInfo) -> None: ...

    def on_response(self, resp: ResponseInfo) -> None: ...

    def on_error(self, exc: BaseException) -> None: ...
