# Admin Manage API

The `AdminManageAPI` client exposes four admin-only **read-form** endpoints added in v0.6.0.

## Resource grouping

All four endpoints are grouped under `client.admin_manage` (D-v0.6-1), separate from the
`posts`, `users`, or `catalogs` resource clients. They are admin-only read forms, propaedeutic to
the admin write surface: the user credentials write is `client.users.edit_credentials()` (spec 05,
see [Users](users.md#writing-users)), which also offers `client.users.get_credentials_for_edit()`
as an alias of `user_credentials_for_edit()`; the workspace and catalog writes arrive with their
own spec.

## Endpoint scope

Each endpoint returns the full editable state of an entity plus an `occToken` (optimistic
concurrency token) for the write operations. `UserCredentialsForEdit` exposes it as `occ_token`
(the token for `users.edit_credentials()`); the other three facades keep it on `.raw` until their
write spec (D-v0.6-2).

| Method | Path | Facade |
|---|---|---|
| `workspace_for_edit` | `admin/manage/workspaces/{workspaceId}/edit` | `WorkspaceForEdit` |
| `catalog_for_edit` | `admin/manage/catalogs/{catalogId}/edit` | `CatalogForEdit` |
| `catalog_entry_for_edit` | `admin/manage/catalogs/{catalogId}/entries/{entryId}/edit` | `CatalogEntryForEdit` |
| `user_credentials_for_edit` | `admin/manage/users/{userId}/credentials/edit` | `UserCredentialsForEdit` |

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    # Workspace edit form
    ws = client.admin_manage.workspace_for_edit(88)
    print(ws.id, ws.name, ws.member_users_count)
    print(ws.raw.occToken)  # occToken only on .raw until the workspace write spec

    # Catalog edit form
    catalog = client.admin_manage.catalog_for_edit(5)
    print(catalog.id, catalog.name, catalog.community_associations_count)

    # Catalog entry edit form
    entry = client.admin_manage.catalog_entry_for_edit(5, 100)
    print(entry.id, entry.label, entry.external_id, entry.parents_count)

    # User credentials edit form
    creds = client.admin_manage.user_credentials_for_edit(1042)
    print(creds.has_google_credentials, creds.has_custom_credentials, creds.custom_username)
    print(creds.occ_token)  # the token for client.users.edit_credentials()
```

## Field curation (Q-v0.6-1)

Narrow facade properties surface the directly-typed scalar fields of each response DTO, plus
light convenience accessors that dig one level into the nested editable-content blocks (which the
code generator emits as `RootModel[Any]` stubs) for the human-facing name/label/credential flags.
Complex nested structures (the full `contentData`, `communityAssociations`, `parents`, per-provider
credential configs) stay on `.raw`, as does `occToken` for workspace, catalog and catalog entry.

## API Reference

::: pynteracta.api.admin_manage.AdminManageAPI
    options:
      show_source: false
      members:
        - workspace_for_edit
        - catalog_for_edit
        - catalog_entry_for_edit
        - user_credentials_for_edit

## Facade Reference

::: pynteracta.models.facade.admin_manage.WorkspaceForEdit

::: pynteracta.models.facade.admin_manage.CatalogForEdit

::: pynteracta.models.facade.admin_manage.CatalogEntryForEdit

::: pynteracta.models.facade.admin_manage.UserCredentialsForEdit
