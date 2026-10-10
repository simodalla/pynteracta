# SPDX-License-Identifier: Apache-2.0
"""Facade models for the communication settings / catalogs endpoints.

Endpoints covered:
  POST /communication/settings/post-definition/catalogs                          (endpoint 6)
  POST /communication/settings/post-definition/catalogs/{catalogId}/entries      (endpoint 7)

Scritture admin (spec 06): le risposte di ``POST|PUT admin/manage/catalogs[/{id}]``,
``…/entries[/{id}]`` e ``…/deleted`` sono avvolte da :class:`CatalogWriteResult`,
:class:`CatalogEntryWriteResult` e :class:`CatalogDeletedResult`.
"""

from __future__ import annotations

from typing import Any

from pynteracta.models.facade.admin_manage import _resolve_root
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

    @property
    def etag(self) -> int | None:
        """Versione del catalogo restituita dal server."""
        return self.raw.etag

    @property
    def entries_typed(self) -> list[CatalogEntry]:
        """Voci del catalogo, se la risposta le contiene, come façade :class:`CatalogEntry`."""
        return [CatalogEntry.from_stub(stub) for stub in self.raw.entries or []]

    @classmethod
    def from_raw(cls, raw: generated.CatalogDTOModel) -> Catalog:
        """Wrap a generated DTO."""
        return cls(raw)

    @classmethod
    def from_stub(cls, stub: generated.CatalogDTO) -> Catalog:
        """Rivalida uno stub ``CatalogDTO`` in :class:`Catalog`."""
        root = _resolve_root(stub)
        if isinstance(root, dict):
            return cls(generated.CatalogDTOModel.model_validate(root))
        msg = f"Unexpected stub root type: {type(root)}"
        raise ValueError(msg)


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

    @property
    def catalog_id(self) -> int | None:
        """Id del catalogo a cui appartiene la voce."""
        return self.raw.catalogId

    @property
    def deleted(self) -> bool | None:
        """Se la voce è disabilitata (cancellazione logica)."""
        return self.raw.deleted

    @classmethod
    def from_raw(cls, raw: generated.CatalogEntryDTO1) -> CatalogEntry:
        """Wrap a generated DTO."""
        return cls(raw)

    @classmethod
    def from_stub(cls, stub: generated.CatalogEntryDTO) -> CatalogEntry:
        """Rivalida uno stub ``CatalogEntryDTO`` in :class:`CatalogEntry`."""
        root = _resolve_root(stub)
        if isinstance(root, dict):
            return cls(generated.CatalogEntryDTO1.model_validate(root))
        msg = f"Unexpected stub root type: {type(root)}"
        raise ValueError(msg)


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


class CatalogWriteResult:
    """Façade sulla risposta di ``catalogs.create`` ed ``catalogs.edit`` (spec 06).

    Attributes:
        raw: Il DTO generato ``CreateEditCatalogResponseDTO``.
    """

    def __init__(
        self, raw: generated.CreateEditCatalogResponseDTO, *, catalog_id: int | None = None
    ) -> None:
        self.raw = raw
        self._catalog_id = catalog_id

    @property
    def catalog(self) -> Catalog | None:
        """Il catalogo scritto, come restituito dal server."""
        return Catalog.from_stub(self.raw.catalog) if self.raw.catalog is not None else None

    @property
    def parent_catalog(self) -> Catalog | None:
        """Il catalogo parent, se c'è."""
        parent = self.raw.parentCatalog
        return Catalog.from_stub(parent) if parent is not None else None

    @property
    def catalog_id(self) -> int | None:
        """Id del catalogo: dalla risposta, altrimenti quello passato dal chiamante."""
        catalog = self.catalog
        if catalog is not None and catalog.id is not None:
            return catalog.id
        return self._catalog_id

    @property
    def next_occ_token(self) -> int | None:
        """Token di concorrenza da usare per la modifica successiva."""
        return self.raw.occToken

    @classmethod
    def from_dict(cls, data: dict[str, Any], catalog_id: int | None = None) -> CatalogWriteResult:
        """Legge la risposta grezza; ``catalog_id`` completa le risposte senza catalogo."""
        return cls(
            generated.CreateEditCatalogResponseDTO.model_validate(data), catalog_id=catalog_id
        )


class CatalogEntryWriteResult:
    """Façade sulla risposta di ``catalogs.create_entry`` ed ``catalogs.edit_entry`` (spec 06).

    Attributes:
        raw: Il DTO generato ``CreateEditCatalogEntryResponseDTO``.
    """

    def __init__(
        self,
        raw: generated.CreateEditCatalogEntryResponseDTO,
        *,
        catalog_id: int | None = None,
        entry_id: int | None = None,
    ) -> None:
        self.raw = raw
        self._catalog_id = catalog_id
        self._entry_id = entry_id

    @property
    def entry(self) -> CatalogEntry | None:
        """La voce scritta, come restituita dal server."""
        return CatalogEntry.from_stub(self.raw.entry) if self.raw.entry is not None else None

    @property
    def catalog_id(self) -> int | None:
        """Id del catalogo: dalla voce restituita, altrimenti quello passato."""
        entry = self.entry
        if entry is not None and entry.catalog_id is not None:
            return entry.catalog_id
        return self._catalog_id

    @property
    def entry_id(self) -> int | None:
        """Id della voce: dalla risposta, altrimenti quello passato."""
        entry = self.entry
        if entry is not None and entry.id is not None:
            return entry.id
        return self._entry_id

    @property
    def next_occ_token(self) -> int | None:
        """Token di concorrenza da usare per la modifica successiva."""
        return self.raw.occToken

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], catalog_id: int | None, entry_id: int | None = None
    ) -> CatalogEntryWriteResult:
        """Legge la risposta grezza; gli id completano le risposte senza voce."""
        return cls(
            generated.CreateEditCatalogEntryResponseDTO.model_validate(data),
            catalog_id=catalog_id,
            entry_id=entry_id,
        )


class CatalogDeletedResult:
    """Façade sulla risposta di ``set_deleted`` e ``set_entry_deleted`` (spec 06).

    Lo swagger dichiara per entrambi gli endpoint la risposta del catalogo (``catalogId``) ma
    definisce anche un DTO con ``entryId``: la façade legge l'id presente e completa l'altro con
    quello passato dal chiamante.

    Attributes:
        raw: ``EditCatalogDeletedResponseDTO`` o ``EditCatalogEntryDeletedResponseDTO``.
    """

    def __init__(
        self,
        raw: generated.EditCatalogDeletedResponseDTO | generated.EditCatalogEntryDeletedResponseDTO,
        *,
        catalog_id: int | None = None,
        entry_id: int | None = None,
    ) -> None:
        self.raw = raw
        self._catalog_id = catalog_id
        self._entry_id = entry_id

    @property
    def catalog_id(self) -> int | None:
        """Id del catalogo: dalla risposta, altrimenti quello passato."""
        value: int | None = getattr(self.raw, "catalogId", None)
        return value if value is not None else self._catalog_id

    @property
    def entry_id(self) -> int | None:
        """Id della voce (``None`` per un catalogo): dalla risposta, altrimenti quello passato."""
        value: int | None = getattr(self.raw, "entryId", None)
        return value if value is not None else self._entry_id

    @property
    def deleted(self) -> bool | None:
        """Il valore del flag ``deleted`` dopo la scrittura."""
        return self.raw.deleted

    @classmethod
    def from_dict(
        cls, data: dict[str, Any], catalog_id: int | None, entry_id: int | None = None
    ) -> CatalogDeletedResult:
        """Sceglie il DTO dalla chiave presente (``entryId`` o ``catalogId``)."""
        raw: generated.EditCatalogDeletedResponseDTO | generated.EditCatalogEntryDeletedResponseDTO
        if "entryId" in data:
            raw = generated.EditCatalogEntryDeletedResponseDTO.model_validate(data)
        else:
            raw = generated.EditCatalogDeletedResponseDTO.model_validate(data)
        return cls(raw, catalog_id=catalog_id, entry_id=entry_id)
