# Admin Manage API

The `AdminManageAPI` client exposes four admin-only **read-form** endpoints, added in v0.6.0, and
the workspace write `edit_workspace()`.

## Resource grouping

All these endpoints are grouped under `client.admin_manage` (D-v0.6-1), separate from the
`posts`, `users`, or `catalogs` resource clients. The other admin writes live on their resource:
the user credentials on `client.users.edit_credentials()` (see
[Users](users.md#writing-users)), catalogs and entries on `client.catalogs` (see
[catalogs](catalogs.md)). `client.users.get_credentials_for_edit()`,
`client.catalogs.get_for_edit()` and `client.catalogs.get_entry_for_edit()` are aliases of the
read forms below.

## Endpoint scope

Each read form returns the full editable state of an entity plus an `occToken` (optimistic
concurrency token) for the write operations. Every facade exposes it as `occ_token`;
`CatalogForEdit` also exposes `parent_catalog_id`.

| Method | Path | Facade |
|---|---|---|
| `workspace_for_edit` | `GET admin/manage/workspaces/{workspaceId}/edit` | `WorkspaceForEdit` |
| `catalog_for_edit` | `GET admin/manage/catalogs/{catalogId}/edit` | `CatalogForEdit` |
| `catalog_entry_for_edit` | `GET admin/manage/catalogs/{catalogId}/entries/{entryId}/edit` | `CatalogEntryForEdit` |
| `user_credentials_for_edit` | `GET admin/manage/users/{userId}/credentials/edit` | `UserCredentialsForEdit` |
| `edit_workspace` | `PUT admin/manage/workspaces/{workspaceId}/{occToken}` | `WorkspaceForEdit` |

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    # Workspace edit form
    ws = client.admin_manage.workspace_for_edit(88)
    print(ws.id, ws.name, ws.member_users_count, ws.occ_token)

    # Catalog edit form
    catalog = client.admin_manage.catalog_for_edit(5)
    print(catalog.id, catalog.name, catalog.parent_catalog_id, catalog.occ_token)

    # Catalog entry edit form
    entry = client.admin_manage.catalog_entry_for_edit(5, 100)
    print(entry.id, entry.label, entry.external_id, entry.parents_count)

    # User credentials edit form
    creds = client.admin_manage.user_credentials_for_edit(1042)
    print(creds.has_google_credentials, creds.has_custom_credentials, creds.custom_username)
    print(creds.occ_token)  # the token for client.users.edit_credentials()
```

## Editing a workspace

```python
with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    ws = client.admin_manage.workspace_for_edit(88)
    cover = client.attachments.upload("cover.png")
    client.admin_manage.edit_workspace(
        88,
        ws.occ_token,
        name=ws.name,  # required on every edit
        translations=ws.translations,
        description=ws.description,
        add_user_ids=[1042],
        add_user_role_associations=[{"userId": 1042, "roleId": 4}],
        new_cover_image_content_ref=cover.content_ref,
    )
    ws = client.admin_manage.workspace_for_edit(88)  # fresh counts
```

`edit_workspace(workspace_id, occ_token, ...)` sends the `occToken` **in the path** and only the
fields given in the body; it also takes `remove_user_ids`, `add_group_ids`, `remove_group_ids`,
`add_group_role_associations` (`{"groupId", "roleId"}`), `remove_role_association_ids` and
`new_logo_content_ref`. The cover and logo `contentRef` come from `client.attachments.upload()`.
`edit_workspace_raw(workspace_id, occ_token, req)` takes an `EditWorkspaceRequestDTO`.

What the test tenant does (verified):

- the **name is required** on every edit: without it the server answers `400` with
  `REQUIRED_FIELD` on `name`, also when only members change. Pass the name, translations and
  description as read; `admin-manage edit-workspace` in the CLI does it for you. Whether omitted
  translations and description are cleared was not tested, to protect the shared test workspace;
- the response is the workspace form: its `occ_token` is the token for the next edit, but its
  **user and group counts are 0**. Read the form again for the real counts (the CLI does);
- one request, never retried: a `409` raises `ConcurrencyError`.

## Field curation (Q-v0.6-1)

Narrow facade properties surface the directly-typed scalar fields of each response DTO, plus
light convenience accessors that dig one level into the nested editable-content blocks (which the
code generator emits as `RootModel[Any]` stubs) for the human-facing name/label/credential flags.
Complex nested structures (the full `contentData`, `communityAssociations`, `parents`, per-provider
credential configs, the paginated member lists of the workspace) stay on `.raw`. Languages whose
value is `null` in a name, label, translation or description map are dropped from the facades:
the generated models accept strings only.

## API Reference

::: pynteracta.api.admin_manage.AdminManageAPI
    options:
      show_source: false
      members:
        - workspace_for_edit
        - catalog_for_edit
        - catalog_entry_for_edit
        - user_credentials_for_edit
        - edit_workspace
        - edit_workspace_raw

## Facade Reference

::: pynteracta.models.facade.admin_manage.WorkspaceForEdit

::: pynteracta.models.facade.admin_manage.CatalogForEdit

::: pynteracta.models.facade.admin_manage.CatalogEntryForEdit

::: pynteracta.models.facade.admin_manage.UserCredentialsForEdit
