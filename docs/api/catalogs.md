# catalogs API

`client.catalogs` reads the post-definition catalogs and their entries, and writes catalogs and
entries through the admin endpoints (admin permissions required).

## Reading

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    catalogs = client.catalogs.list([5, 8], load_entries=True)
    for catalog in catalogs.items_typed:
        print(catalog.id, catalog.name, catalog.paged)

    for entry in client.catalogs.iterate_entries(5, page_size=50):
        print(entry.id, entry.label, entry.external_id)
```

A disabled catalog is no longer returned: `list([id])` with a disabled catalog answers `400` with
`NOT_EXISTS` on `catalogIds`.

## Edit forms

`get_for_edit(catalog_id)` and `get_entry_for_edit(catalog_id, entry_id)` read the admin edit
forms. They are aliases of `client.admin_manage.catalog_for_edit()` and
`catalog_entry_for_edit()`: same request, same facade. Each facade exposes `occ_token`, the
concurrency token for the next edit; `CatalogForEdit` also exposes `parent_catalog_id`. Languages
whose value is `null` in a name or label map are dropped from the facade.

## Writing catalogs

```python
with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    created = client.catalogs.create(name={"it": "Sedi", "en": "Sites"}, parent_id=3)
    print(created.catalog_id, created.next_occ_token)

    form = client.catalogs.get_for_edit(created.catalog_id)
    # The name map is replaced as a whole: pass every language you want to keep.
    edited = client.catalogs.edit(
        created.catalog_id, form.occ_token, name={**form.name, "en": "Offices"}
    )

    client.catalogs.set_deleted(created.catalog_id, True)   # logical deletion
    client.catalogs.set_deleted(created.catalog_id, False)  # restore
```

- `create(name=..., parent_id=...)` and `edit(catalog_id, occ_token, name=..., parent_id=...)`
  send **only the fields given** and return a `CatalogWriteResult` (`catalog_id`, `catalog`,
  `parent_catalog`, `next_occ_token`, `.raw`).
- `set_deleted(catalog_id, deleted)` changes the logical `deleted` flag (no `occToken` needed)
  and returns a `CatalogDeletedResult` (`catalog_id`, `entry_id`, `deleted`, `.raw`). Catalogs
  are never removed: the API has no physical deletion.
- `deleted` is not an argument of `edit`: use `set_deleted`, or `edit_raw` with a
  `CreateEditCatalogRequestDTO` if you need it in the `PUT`.
- `create_raw(req)` and `edit_raw(catalog_id, req)` take a pre-built DTO.

**Omitted fields** (verified on the test tenant): the server **replaces the whole name map** on
every edit. The languages missing from `name` lose their text, and the `it` language takes the
text you passed. Read the form and send the full map, as above; `catalogs edit` in the CLI does
it for you.

## Writing catalog entries

```python
with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    entry = client.catalogs.create_entry(5, label={"it": "Bologna"}, external_id="BO")
    form = client.catalogs.get_entry_for_edit(5, entry.entry_id)
    client.catalogs.edit_entry(
        5,
        entry.entry_id,
        form.occ_token,
        label={**form.label, "en": "Bologna"},
        external_id=form.external_id,
    )
    client.catalogs.set_entry_deleted(5, entry.entry_id, True)
```

- `create_entry(catalog_id, label=..., parent_ids=..., external_id=...)` and
  `edit_entry(catalog_id, entry_id, occ_token, ...)` return a `CatalogEntryWriteResult`
  (`entry_id`, `catalog_id`, `entry`, `next_occ_token`, `.raw`).
- `set_entry_deleted(catalog_id, entry_id, deleted)` returns a `CatalogDeletedResult`. The swagger
  declares the catalog response (`catalogId`), but the tenant answers with `entryId`: the result
  always has both ids, completing the missing one with the id you passed.

**Omitted fields** (verified on the test tenant): the label map is replaced as a whole, like the
catalog name, and the **external id and the parent entries missing from the request are
cleared**. Send them back from the form, as above; `catalogs edit-entry` in the CLI does it for
you.

Every write sends one request and never retries: a `409` raises `ConcurrencyError`, a timeout or
network error raises `TransportError` with an unknown outcome (ADR 0001).

## API Reference

::: pynteracta.api.catalogs.CatalogsAPI
    options:
      show_source: false
      members:
        - list
        - list_raw
        - entries
        - entries_raw
        - iterate_entries
        - get_for_edit
        - get_entry_for_edit
        - create
        - create_raw
        - edit
        - edit_raw
        - set_deleted
        - create_entry
        - create_entry_raw
        - edit_entry
        - edit_entry_raw
        - set_entry_deleted

---

## Facade models

::: pynteracta.models.facade.catalogs.CatalogList

::: pynteracta.models.facade.catalogs.Catalog

::: pynteracta.models.facade.catalogs.CatalogEntryList

::: pynteracta.models.facade.catalogs.CatalogEntry

::: pynteracta.models.facade.catalogs.CatalogWriteResult

::: pynteracta.models.facade.catalogs.CatalogEntryWriteResult

::: pynteracta.models.facade.catalogs.CatalogDeletedResult
