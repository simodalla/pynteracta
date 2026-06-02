# SPDX-License-Identifier: Apache-2.0
"""Facade models for the communication settings / catalogs endpoints.

Endpoints covered:
  POST /communication/settings/post-definition/catalogs                          (endpoint 6)
  POST /communication/settings/post-definition/catalogs/{catalogId}/entries      (endpoint 7)
"""

from __future__ import annotations

from pynteracta.models.generated import external_v2 as generated

# Re-exported for use by the catalogs API layer.
GetPostDefinitionCatalogsRequestDTO = generated.GetPostDefinitionCatalogsRequestDTO
ListPostDefinitionCatalogEntriesRequestDTO = generated.ListPostDefinitionCatalogEntriesRequestDTO


class Catalog:
    """Narrow facade over :class:`~generated.CatalogDTOModel`.

    Attributes:
        raw: The underlying generated DTO; access additional fields via this escape hatch.
    """

    def __init__(self, raw: generated.CatalogDTOModel) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Unique catalog identifier."""
        return self.raw.id

    @property
    def name(self) -> str | None:
        """Catalog name."""
        return self.raw.name

    @property
    def paged(self) -> bool | None:
        """Whether this catalog is paginated."""
        return self.raw.paged

    @classmethod
    def from_raw(cls, raw: generated.CatalogDTOModel) -> Catalog:
        """Wrap a generated DTO."""
        return cls(raw)


class CatalogList:
    """Facade over :class:`~generated.GetPostDefinitionCatalogsResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.GetPostDefinitionCatalogsResponseDTO) -> None:
        self.raw = raw

    @property
    def items(self) -> list[generated.CatalogDTO]:
        """Raw catalog items (generated stubs)."""
        return self.raw.catalogs or []

    @property
    def items_typed(self) -> list[Catalog]:
        """Catalog items re-validated as typed :class:`Catalog` facades."""
        result = []
        for stub in self.items:
            typed = generated.CatalogDTOModel.model_validate(stub.root)
            result.append(Catalog(typed))
        return result

    @classmethod
    def from_dict(cls, data: dict) -> CatalogList:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.GetPostDefinitionCatalogsResponseDTO.model_validate(data))


class CatalogEntry:
    """Narrow facade over :class:`~generated.CatalogEntryDTO1`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.CatalogEntryDTO1) -> None:
        self.raw = raw

    @property
    def id(self) -> int | None:
        """Unique entry identifier."""
        return self.raw.id

    @property
    def label(self) -> str | None:
        """Entry label (display value)."""
        return self.raw.label

    @property
    def external_id(self) -> str | None:
        """External identifier for this entry."""
        return self.raw.externalId

    @property
    def parent_ids(self) -> list[int] | None:
        """Parent entry identifiers (for hierarchical catalogs)."""
        return self.raw.parentIds

    @classmethod
    def from_raw(cls, raw: generated.CatalogEntryDTO1) -> CatalogEntry:
        """Wrap a generated DTO."""
        return cls(raw)


class CatalogEntryList:
    """Facade over :class:`~generated.ListPostDefinitionCatalogEntriesResponseDTO`.

    Attributes:
        raw: The underlying generated DTO.
    """

    def __init__(self, raw: generated.ListPostDefinitionCatalogEntriesResponseDTO) -> None:
        self.raw = raw

    @property
    def items(self) -> list[generated.CatalogEntryDTO]:
        """Raw entry items (generated stubs)."""
        return self.raw.items or []

    @property
    def items_typed(self) -> list[CatalogEntry]:
        """Entry items re-validated as typed :class:`CatalogEntry` facades."""
        result = []
        for stub in self.items:
            typed = generated.CatalogEntryDTO1.model_validate(stub.root)
            result.append(CatalogEntry(typed))
        return result

    @property
    def next_page_token(self) -> str | None:
        """Token for the next page, or ``None`` on the last page."""
        return self.raw.nextPageToken

    @property
    def total_items_count(self) -> int | None:
        """Total entry count (present only when ``calculateTotalItemsCount`` was requested)."""
        return self.raw.totalItemsCount

    @classmethod
    def from_dict(cls, data: dict) -> CatalogEntryList:  # type: ignore[type-arg]
        """Parse from a raw API response dict."""
        return cls(generated.ListPostDefinitionCatalogEntriesResponseDTO.model_validate(data))
