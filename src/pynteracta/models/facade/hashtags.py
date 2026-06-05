# SPDX-License-Identifier: Apache-2.0
"""Facade models for the hashtags endpoints."""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated

AdminListHashtagsRequestDTO = generated.AdminListHashtagsRequestDTO


def _resolve_root(obj: object) -> object:
    """Unwrap a RootModel stub to its inner dict."""
    root = getattr(obj, "root", None)
    return root if root is not None else obj


class Hashtag:
    """Thin facade over :class:`~generated.AdminHashtagDTO`.

    ``AdminListHashtagsResponseDTO.items`` are typed as ``AdminHashtagDTOModel``
    (``RootModel[Any]`` stubs); the typed sibling is the plain ``AdminHashtagDTO``.

    Attributes:
        raw: The underlying typed DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.AdminHashtagDTO) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        return self.raw.id

    @property
    def name(self) -> str | None:
        return self.raw.name

    @property
    def community_id(self) -> int | None:
        return self.raw.communityId

    @property
    def external_id(self) -> str | None:
        return self.raw.externalId

    @property
    def deleted(self) -> bool | None:
        return self.raw.deleted

    @classmethod
    def from_dict(cls, data: dict) -> Hashtag:  # type: ignore[type-arg]
        """Parse from a raw dict item."""
        raw = generated.AdminHashtagDTO.model_validate(data)
        return cls(raw)


class HashtagList:
    """Narrow facade over :class:`~generated.AdminListHashtagsResponseDTO`.

    ``items`` are ``AdminHashtagDTOModel`` (``RootModel[Any]`` stubs); call
    :meth:`items_typed` to get :class:`Hashtag` instances.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.AdminListHashtagsResponseDTO) -> None:
        self.raw = raw

    @property
    def next_page_token(self) -> str | None:
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        return self.raw.totalItemsCount

    @property
    def items_typed(self) -> list[Hashtag]:
        """Re-validate each opaque ``AdminHashtagDTOModel`` stub into :class:`Hashtag`."""
        if not self.raw.items:
            return []
        result = []
        for item in self.raw.items:
            root = _resolve_root(item)
            if isinstance(root, dict):
                result.append(Hashtag(generated.AdminHashtagDTO.model_validate(root)))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> HashtagList:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        raw = generated.AdminListHashtagsResponseDTO.model_validate(data)
        return cls(raw)
