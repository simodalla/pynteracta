# SPDX-License-Identifier: Apache-2.0
"""Facade models for the users endpoints.

Endpoints covered:
  POST /admin/data/users                         (endpoint 3 — list system users)
  GET  /core/user-profile/info                   (endpoint 4 — own profile)
  GET  /admin/manage/users/{userId}/edit         (endpoint 5 — user for edit)
"""

from __future__ import annotations

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
