# SPDX-License-Identifier: Apache-2.0
"""Authentication resource client (endpoints 1-2)."""

from __future__ import annotations

from typing import Any

from pynteracta.api._base import ResourceClient
from pynteracta.models.facade.auth import (
    CreateAccessTokenByServiceAccountRequestDTO,
    CurrentUserResponse,
    ServiceAccountTokenResponse,
)
from pynteracta.transport import HttpTransport

_CURRENT_USER_PATH = "core/auth/current-user-data"
_CREATE_TOKEN_PATH = "core/auth/create-access-token-by-service-account"


class AuthAPI(ResourceClient):
    """Client for ``/core/auth/*`` endpoints."""

    def __init__(
        self,
        transport: HttpTransport,
        *,
        unauthenticated_transport: HttpTransport | None = None,
    ) -> None:
        super().__init__(transport)
        self._unauth_transport = unauthenticated_transport or transport

    def current_user_data(self) -> CurrentUserResponse:
        """GET ``/core/auth/current-user-data`` — identity of the authenticated principal."""
        return CurrentUserResponse.from_dict(self._get(_CURRENT_USER_PATH))

    def create_access_token_raw(
        self,
        req: CreateAccessTokenByServiceAccountRequestDTO,
    ) -> ServiceAccountTokenResponse:
        """POST ``/core/auth/create-access-token-by-service-account`` (escape hatch).

        Uses the unauthenticated transport so no bearer token is sent with the
        service-account assertion request.
        """
        response = self._unauth_transport.request(
            "POST",
            _CREATE_TOKEN_PATH,
            json=req.model_dump(mode="json", exclude_none=True),
        )
        body: Any = response.json()
        if not isinstance(body, dict):
            msg = "Expected JSON object response from create-access-token"
            raise TypeError(msg)
        return ServiceAccountTokenResponse.from_dict(body)
