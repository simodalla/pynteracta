# SPDX-License-Identifier: Apache-2.0
"""Facade models for the admin/manage edit (read-form) endpoints.

These four facades wrap the *for-edit* response DTOs returned by the admin/manage surface.
Each response carries an ``occToken`` (optimistic-concurrency token) intended for the future
write line (deferred to v1.0+); it is **only** reachable through ``.raw`` — it is never surfaced
as a narrow property, to keep the read facade free of write-only concerns.

Field-curation strategy (answer to Q-v0.6-1): narrow properties surface the directly-typed
scalar fields of each response DTO, plus light convenience accessors that dig one level into the
nested editable-content blocks (which the code generator emits as ``RootModel[Any]`` stubs) for
the human-facing name/label/credential flags. Complex nested structures and ``occToken`` stay on
``.raw``.
"""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated


def _resolve_root(obj: object) -> object:
    """Unwrap a ``RootModel`` stub to its inner value (typically a dict)."""
    root = getattr(obj, "root", None)
    return root if root is not None else obj


class WorkspaceForEdit:
    """Narrow facade over :class:`~generated.GetWorkspaceForEditResponseDTO`.

    The editable payload (``name``, ``description``, members, …) lives in ``contentData``, which
    the generator emits as a ``RootModel[Any]`` stub; :attr:`name` and :attr:`description`
    re-validate it into the typed sibling for convenience. ``occToken`` is only on ``.raw`` — it is
    the propaedeutic edit token for the future write surface.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetWorkspaceForEditResponseDTO) -> None:
        self.raw = raw
        self._content = self._typed_content(raw)

    @staticmethod
    def _typed_content(
        raw: generated.GetWorkspaceForEditResponseDTO,
    ) -> generated.WorkspaceEditableContentDataDTO1 | None:
        if raw.contentData is None:
            return None
        root = _resolve_root(raw.contentData)
        if isinstance(root, dict):
            return generated.WorkspaceEditableContentDataDTO1.model_validate(root)
        return None

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        """Workspace name (from the editable ``contentData`` block)."""
        return self._content.name if self._content is not None else None

    @property
    def description(self) -> dict[str, str] | None:
        """Internationalized description map (from ``contentData``)."""
        return self._content.description if self._content is not None else None

    @property
    def admin_users_count(self) -> int | None:
        return self.raw.adminUsersCount

    @property
    def admin_groups_count(self) -> int | None:
        return self.raw.adminGroupsCount

    @property
    def member_users_count(self) -> int | None:
        return self.raw.memberUsersCount

    @property
    def member_groups_count(self) -> int | None:
        return self.raw.memberGroupsCount

    @property
    def creation_timestamp(self) -> int | None:
        return self.raw.creationTimestamp

    @property
    def last_modify_timestamp(self) -> int | None:
        return self.raw.lastModifyTimestamp

    @classmethod
    def from_dict(cls, data: dict) -> WorkspaceForEdit:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.GetWorkspaceForEditResponseDTO.model_validate(data))


class CatalogForEdit:
    """Narrow facade over :class:`~generated.GetCatalogForEditResponseDTO`.

    The editable payload (``name`` map, ``parentCatalog``, ``deleted``) lives in ``contentData``,
    a ``RootModel[Any]`` stub re-validated into its typed sibling for :attr:`name` and
    :attr:`deleted`. ``communityAssociations`` (the communities using this catalog) is summarized
    by :attr:`community_associations_count`; the full list stays on ``.raw``. ``occToken`` is only
    on ``.raw``.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetCatalogForEditResponseDTO) -> None:
        self.raw = raw
        self._content = self._typed_content(raw)

    @staticmethod
    def _typed_content(
        raw: generated.GetCatalogForEditResponseDTO,
    ) -> generated.CatalogEditableContentDTOModel | None:
        if raw.contentData is None:
            return None
        root = _resolve_root(raw.contentData)
        if isinstance(root, dict):
            return generated.CatalogEditableContentDTOModel.model_validate(root)
        return None

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> dict[str, str] | None:
        """Internationalized catalog name map (from ``contentData``)."""
        return self._content.name if self._content is not None else None

    @property
    def deleted(self) -> bool | None:
        """Whether the catalog is logically deleted (from ``contentData``)."""
        return self._content.deleted if self._content is not None else None

    @property
    def community_associations_count(self) -> int | None:
        """Number of communities that use this catalog."""
        assocs = self.raw.communityAssociations
        return len(assocs) if assocs is not None else None

    @classmethod
    def from_dict(cls, data: dict) -> CatalogForEdit:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.GetCatalogForEditResponseDTO.model_validate(data))


class CatalogEntryForEdit:
    """Narrow facade over :class:`~generated.GetCatalogEntryForEditResponseDTO`.

    All surfaced fields are directly typed on the response DTO. ``label`` is an internationalized
    map; ``parents`` (the hierarchical parent chain) is summarized by :attr:`parents_count`, with
    the full list available on ``.raw``. ``occToken`` is only on ``.raw``.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetCatalogEntryForEditResponseDTO) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def label(self) -> dict[str, str] | None:
        """Internationalized entry label map."""
        return self.raw.label

    @property
    def external_id(self) -> str | None:
        return self.raw.externalId

    @property
    def deleted(self) -> bool | None:
        return self.raw.deleted

    @property
    def parents_count(self) -> int | None:
        """Number of parent entries (hierarchical dependency chain)."""
        parents = self.raw.parents
        return len(parents) if parents is not None else None

    @classmethod
    def from_dict(cls, data: dict) -> CatalogEntryForEdit:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.GetCatalogEntryForEditResponseDTO.model_validate(data))


class UserCredentialsForEdit:
    """Narrow facade over :class:`~generated.GetUserCredentialsForEditResponseDTO`.

    The response has no entity id (the user id is the path parameter). The credentials payload
    lives in ``userCredentialsConfiguration``, a ``RootModel[Any]`` stub re-validated into its
    typed sibling. Narrow properties expose which credential kinds are configured plus the custom
    username/active flags; the full per-provider configuration stays on ``.raw``. ``occToken`` is
    only on ``.raw``.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.GetUserCredentialsForEditResponseDTO) -> None:
        self.raw = raw
        self._config = self._typed_config(raw)

    @staticmethod
    def _typed_config(
        raw: generated.GetUserCredentialsForEditResponseDTO,
    ) -> generated.UserCredentialsConfigurationDTO1 | None:
        if raw.userCredentialsConfiguration is None:
            return None
        root = _resolve_root(raw.userCredentialsConfiguration)
        if isinstance(root, dict):
            return generated.UserCredentialsConfigurationDTO1.model_validate(root)
        return None

    @staticmethod
    def _typed_custom(
        config: generated.UserCredentialsConfigurationDTO1 | None,
    ) -> generated.CustomUserCredentialsConfigurationDTOModel | None:
        if config is None or config.custom is None:
            return None
        root = _resolve_root(config.custom)
        if isinstance(root, dict):
            return generated.CustomUserCredentialsConfigurationDTOModel.model_validate(root)
        return None

    @property
    def has_google_credentials(self) -> bool:
        return self._config is not None and self._config.google is not None

    @property
    def has_microsoft_credentials(self) -> bool:
        return self._config is not None and self._config.microsoft is not None

    @property
    def has_custom_credentials(self) -> bool:
        return self._config is not None and self._config.custom is not None

    @property
    def custom_username(self) -> str | None:
        """Username of the custom (username/password) credentials, if configured."""
        custom = self._typed_custom(self._config)
        return custom.username if custom is not None else None

    @property
    def custom_active(self) -> bool | None:
        """Whether the custom credentials are active, if configured."""
        custom = self._typed_custom(self._config)
        return custom.active if custom is not None else None

    @classmethod
    def from_dict(cls, data: dict) -> UserCredentialsForEdit:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.GetUserCredentialsForEditResponseDTO.model_validate(data))
