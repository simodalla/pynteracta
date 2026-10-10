# SPDX-License-Identifier: Apache-2.0
"""Facade models for the users endpoints.

Endpoints covered:
  POST /admin/data/users                         (endpoint 3 — list system users)
  GET  /core/user-profile/info                   (endpoint 4 — own profile)
  GET  /admin/manage/users/{userId}/edit         (endpoint 5 — user for edit)
  POST /admin/manage/users                       (spec 05 — create)
  PUT  /admin/manage/users/{userId}              (spec 05 — edit)
  PUT  /admin/manage/users/{userId}/credentials  (spec 05 — edit credentials)
"""

from __future__ import annotations

from typing import Any

from pynteracta.models.generated import external_v2 as generated

# Re-exported for use by the users API layer (M5).
ListSystemUsersRequestDTO = generated.ListSystemUsersRequestDTO


class SystemUserList:
    """Narrow facade over :class:`~generated.ListSystemUsersResponseDTO`.

    The ``items`` list holds :class:`~generated.ListSystemUsersElementDTO` objects, which are
    generated as ``RootModel[Any]`` stubs.  Call :meth:`items_typed` to re-validate each item
    against the fully-typed :class:`~generated.ListSystemUsersElementDTOModel`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.ListSystemUsersResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        """Token for the next page, or ``None`` if this is the last page."""
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        """Total number of matching users (only populated when requested)."""
        return self.raw.totalItemsCount

    @property
    def items_typed(self) -> list[generated.ListSystemUsersElementDTOModel]:
        """Re-validate each opaque list item into the typed element DTO.

        Returns:
            List of :class:`~generated.ListSystemUsersElementDTOModel` instances.
        """
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = item.root if hasattr(item, "root") else item
            if isinstance(root, dict):
                result.append(generated.ListSystemUsersElementDTOModel.model_validate(root))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> SystemUserList:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`SystemUserList`.
        """
        raw = generated.ListSystemUsersResponseDTO.model_validate(data)
        return cls(raw)


class UserProfile:
    """Narrow facade over :class:`~generated.UserProfileInfoDTO1`.

    Note: The endpoint schema references ``UserProfileInfoDTO``, which is generated as a
    ``RootModel[Any]`` stub due to a Swagger 2.0 name collision.  This facade wraps
    ``UserProfileInfoDTO1``, the properly typed equivalent.  See PROGRESS.md § M3 for
    details.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.UserProfileInfoDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Unique user identifier."""
        return self.raw.id

    @property
    def first_name(self) -> str | None:
        """User first name."""
        return self.raw.firstName

    @property
    def last_name(self) -> str | None:
        """User last name."""
        return self.raw.lastName

    @property
    def caption(self) -> str | None:
        """Display caption (usually ``FirstName LastName``)."""
        return self.raw.caption

    @property
    def contact_email(self) -> str | None:
        """Contact email address."""
        return self.raw.contactEmail

    @property
    def account_photo_url(self) -> str | None:
        """URL of the user's profile photo."""
        return self.raw.accountPhotoUrl

    @classmethod
    def from_dict(cls, data: dict) -> UserProfile:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`UserProfile`.
        """
        raw = generated.UserProfileInfoDTO1.model_validate(data)
        return cls(raw)


class UserForEdit:
    """Narrow facade over :class:`~generated.GetUserForEditResponseDTO`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetUserForEditResponseDTO) -> None:
        self.raw = raw

    @property
    def first_name(self) -> str | None:
        """User first name."""
        return self.raw.firstname

    @property
    def last_name(self) -> str | None:
        """User last name."""
        return self.raw.lastname

    @property
    def contact_email(self) -> str | None:
        """Primary contact email."""
        return self.raw.contactEmail

    @property
    def external_id(self) -> str | None:
        """External system identifier."""
        return self.raw.externalId

    @property
    def blocked(self) -> bool | None:
        """Whether the account is blocked."""
        return self.raw.blocked

    @property
    def account_photo_url(self) -> str | None:
        """URL of the user's current profile photo."""
        return self.raw.accountPhotoUrl

    @property
    def occ_token(self) -> int | None:
        """Token di concorrenza da passare a ``edit`` (spec 05, RF-023a)."""
        return self.raw.occToken

    @classmethod
    def from_dict(cls, data: dict) -> UserForEdit:  # type: ignore[type-arg]
        """Parse from a raw API response dict.

        Args:
            data: Parsed JSON response body.

        Returns:
            A new :class:`UserForEdit`.
        """
        raw = generated.GetUserForEditResponseDTO.model_validate(data)
        return cls(raw)


class UserWriteResult:
    """Façade sulla risposta di ``create``, ``edit`` ed ``edit_credentials`` di un utente.

    I tre DTO di risposta non hanno gli stessi campi: le proprietà assenti valgono ``None``.
    ``user_id`` viene dalla risposta di creazione; per le modifiche è quello passato dal
    chiamante, perché il server non lo restituisce.

    Attributes:
        raw: Il DTO generato sottostante (``CreateUserResponseDTO``, ``EditUserResponseDTO`` o
            ``EditUserCredentialsResponseDTO``).
    """

    def __init__(
        self,
        raw: (
            generated.CreateUserResponseDTO
            | generated.EditUserResponseDTO
            | generated.EditUserCredentialsResponseDTO
        ),
        *,
        user_id: int | None = None,
    ) -> None:
        self.raw = raw
        self._user_id = user_id

    @property
    def user_id(self) -> int | None:
        """Id dell'utente scritto: dalla risposta di creazione, altrimenti quello passato."""
        user_id = getattr(self.raw, "userId", None)
        if user_id is not None:
            return int(user_id)
        return self._user_id

    @property
    def next_occ_token(self) -> int | None:
        """Token di concorrenza da usare per la modifica successiva."""
        return self.raw.nextOccToken

    @property
    def generated_password(self) -> list[str] | None:
        """Password custom generata dal server alla creazione, se richiesta."""
        value: list[str] | None = getattr(self.raw, "generatedPassword", None)
        return value

    @property
    def expired_credentials(self) -> bool | None:
        """Se le credenziali custom create vanno cambiate al primo accesso."""
        value: bool | None = getattr(self.raw, "expiredCredentials", None)
        return value

    @property
    def sent_email_notify(self) -> bool | None:
        """Se il server ha inviato l'email di notifica delle credenziali."""
        value: bool | None = getattr(self.raw, "sentEmailNotify", None)
        return value

    @property
    def account_photo_url(self) -> str | None:
        """URL della foto dell'utente dopo la scrittura."""
        value: str | None = getattr(self.raw, "accountPhotoUrl", None)
        return value

    @classmethod
    def from_create(cls, data: dict[str, Any]) -> UserWriteResult:
        """Legge la risposta di ``POST admin/manage/users``."""
        return cls(generated.CreateUserResponseDTO.model_validate(data))

    @classmethod
    def from_edit(cls, data: dict[str, Any], user_id: int) -> UserWriteResult:
        """Legge la risposta di ``PUT admin/manage/users/{userId}``."""
        return cls(generated.EditUserResponseDTO.model_validate(data), user_id=user_id)

    @classmethod
    def from_credentials(cls, data: dict[str, Any], user_id: int) -> UserWriteResult:
        """Legge la risposta di ``PUT admin/manage/users/{userId}/credentials``."""
        return cls(generated.EditUserCredentialsResponseDTO.model_validate(data), user_id=user_id)
