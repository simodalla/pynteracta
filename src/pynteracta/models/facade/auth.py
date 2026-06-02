# SPDX-License-Identifier: Apache-2.0
"""Facade models for the authentication endpoints.

Endpoints covered:
  POST /core/auth/create-access-token-by-service-account                      (endpoint 1)
  GET  /core/auth/current-user-data                                           (endpoint 2)
  POST /core/auth/create-access-token-by-google-oauth2-access-token-credentials  (endpoint 3)
"""

from __future__ import annotations

from pydantic import ConfigDict

from pynteracta.models.generated import external_v2 as generated

# Re-exported for use by the auth API layer (M4/M5).
CreateAccessTokenByServiceAccountRequestDTO = generated.CreateAccessTokenByServiceAccountRequestDTO


class ServiceAccountTokenResponse:
    """Narrow facade over :class:`~generated.CreateAccessTokenByServiceAccountResponseDTO`.

    Note (Q3 — M4 follow-up): The response contains only ``accessToken``; there is no
    ``expiresIn`` / ``expiresAt`` field.  Token expiry must be decoded from the JWT ``exp``
    claim.  See PROGRESS.md § M3 → Follow-ups.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.CreateAccessTokenByServiceAccountResponseDTO) -> None:
        self.raw = raw

    @property
    def access_token(self) -> str | None:
        """Raw access token string (JWT)."""
        return self.raw.accessToken

    @classmethod
    def from_dict(cls, data: dict) -> ServiceAccountTokenResponse:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`ServiceAccountTokenResponse`.
        """
        raw = generated.CreateAccessTokenByServiceAccountResponseDTO.model_validate(data)
        return cls(raw)


class GoogleOAuth2AccessTokenResponse:
    """Facade over the Google-OAuth2 token-exchange response.

    The exchange endpoint
    ``POST /core/auth/create-access-token-by-google-oauth2-access-token-credentials`` is not
    present in the pinned ``swagger.json``, so there is no generated DTO for it.  The response
    envelope mirrors the service-account flow.  The vendor prose names the field
    ``access_token`` while the service-account envelope uses ``accessToken``; this facade
    tolerates both (verified at integration).

    Attributes:
        raw: The parsed response dict; access additional fields via this escape hatch.
    """

    def __init__(self, raw: dict) -> None:  # type: ignore[type-arg]
        self.raw = raw

    @property
    def access_token(self) -> str | None:
        """Interacta access token (JWT), or ``None`` if absent."""
        token = self.raw.get("accessToken")
        if token is None:
            token = self.raw.get("access_token")
        return str(token) if token is not None else None

    @classmethod
    def from_dict(cls, data: dict) -> GoogleOAuth2AccessTokenResponse:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`GoogleOAuth2AccessTokenResponse`.
        """
        return cls(dict(data))


class CurrentUserResponse:
    """Narrow facade over :class:`~generated.CurrentUserDataResponseDTO`.

    The ``userData`` nested DTO is typed as ``RootModel[Any]`` in the generated code due to
    a Swagger 2.0 naming collision.  Access it via ``raw.userData.root`` for the full dict, or
    call :meth:`user_data_typed` for a re-validated typed model.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    model_config = ConfigDict(extra="ignore")

    def __init__(self, raw: generated.CurrentUserDataResponseDTO) -> None:
        self.raw = raw

    @property
    def has_google_credentials(self) -> bool | None:
        """Whether the principal has linked Google credentials."""
        return self.raw.hasGoogleCredentials

    @property
    def has_microsoft_credentials(self) -> bool | None:
        """Whether the principal has linked Microsoft credentials."""
        return self.raw.hasMicrosoftCredentials

    @property
    def user_data_typed(self) -> generated.CurrentUserDataDTOModel | None:
        """Re-validate the opaque ``userData`` root into the typed DTO.

        Returns:
            A typed :class:`~generated.CurrentUserDataDTOModel`, or ``None`` if absent.
        """
        if self.raw.userData is None:
            return None
        root = self.raw.userData.root
        if not isinstance(root, dict):
            return None
        return generated.CurrentUserDataDTOModel.model_validate(root)

    @classmethod
    def from_dict(cls, data: dict) -> CurrentUserResponse:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`CurrentUserResponse`.
        """
        raw = generated.CurrentUserDataResponseDTO.model_validate(data)
        return cls(raw)
