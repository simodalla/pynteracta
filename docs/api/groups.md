# Groups API

The `GroupsAPI` client exposes the group read endpoints (list, members, edit form) and, since
the admin write group opened by ADR 0001, the write endpoints: create, edit, delete and the
members edit, for one group or in bulk.

## Resource grouping

All endpoints are grouped under `client.groups` (D-v0.5-1), separate from `PostsAPI` or other
resource clients.

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    # List groups (first page)
    page = client.groups.list_groups()
    for g in page.items_typed:
        print(g.id, g.name, g.members_count)

    # Iterate all pages lazily
    for g in client.groups.iterate_groups(full_text_filter="eng"):
        print(g.id, g.name)

    # List members of a group
    members = client.groups.list_members(201)
    for m in members.members_typed:
        print(m.id, m.full_name, m.email)

    # Iterate all member pages
    for m in client.groups.iterate_members(201, page_size=50):
        print(m.id, m.full_name)

    # Fetch group detail (for-edit form; includes members list and occToken)
    group = client.groups.get_for_edit(201)
    print(group.name, group.members_count)
    print(group.occ_token)  # the token to pass to edit() and edit_members()
```

## Writing groups

`create()`, `edit()`, `delete()`, `edit_members()` and `edit_members_bulk()` follow the other
write groups: explicit keyword arguments, `*_raw()` variants, a facade over the response.
**Only the fields you pass are sent**, in one request.

```python
from pynteracta.client import InteractaClient
from pynteracta.exceptions import ConcurrencyError

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    created = client.groups.create(name="QA", email="qa@tenant.example.com", visible=True)
    print(created.group_id, created.next_occ_token, created.members_count)

    # Edit: read first and send back every field that must survive (see "Omitted fields")
    group = client.groups.get_for_edit(created.group_id)
    edited = client.groups.edit(
        created.group_id,
        group.occ_token,
        name="QA team",
        email=group.email,
        visible=True,
    )
    print(edited.next_occ_token)

    # Members: add and remove by user id, with the token of the group
    group = client.groups.get_for_edit(created.group_id)
    try:
        result = client.groups.edit_members(
            created.group_id, group.occ_token, add_user_ids=[1042], remove_user_ids=[1099]
        )
    except ConcurrencyError:
        raise  # the group changed after we read it: re-read and decide, the library never retries
    print(result.next_occ_token)  # valid for the next members edit

    # Several groups in one request: the server reports successes and conflicts per group
    outcome = client.groups.edit_members_bulk(
        [{"id": 201, "occToken": 5, "addUserIds": [1042]}, {"id": 202, "occToken": 1}]
    )
    print([g.id for g in outcome.success_groups], [g.id for g in outcome.concurrency_error_groups])

    client.groups.delete(created.group_id)
```

### `GroupWriteResult` and `GroupMembersResult`

`create()`, `edit()` and `edit_members()` return a `GroupWriteResult`: `group_id`,
`next_occ_token`, `name`, `email`, `visible`, `members_count` and `.raw`. `delete()` returns
nothing. `edit_members_bulk()` returns a `GroupMembersResult` with `success_groups` and
`concurrency_error_groups`, lists of `GroupSummary` (`id`, `name`, `members_count`, `occ_token`),
and **does not raise** for conflicts: that decision belongs to the caller.

### Concurrency: `occ_token`

`edit()` and `edit_members()` take the token read with `get_for_edit()` (`GroupForEdit.occ_token`).
`edit()` gets a `409` → `ConcurrencyError` when the group changed. The members endpoint answers
`200` even on conflict, listing the group under `concurrencyErrorGroups`: `edit_members()` raises
`ConcurrencyError` with `status_code == 200` and the response body attached. The token returned by
a members edit is valid for the next one (verified on a tenant). The library never re-reads and
retries (ADR 0001).

### Omitted fields in `edit()`: the server replaces the group

Verified against a tenant (spec 05): `edit()` **requires** `name` (`400` `REQUIRED_FIELD`) and
**clears** `email`, `external_id` and `visible` when they are missing from the request (`visible`
becomes `False`, i.e. a system group). The members are the exception: `member_ids` you omit are
kept; when you pass it, it is the **complete** list. Use `edit_members()` to add or remove single
users.

!!! warning "Pass every field you want to keep"
    Read the group first and send back name, email, external id and visibility. The CLI
    `groups edit` does this for you and never touches the members.

### Deleting a group

After `delete()` the group is gone: `get_for_edit()` answers `404` (`NotFoundError`).

## Sort fields for `list_groups`

The API uses `orderTypeId` (not `orderBy`). Valid values: `'name'`, `'email'`.
Pass as `order_type_id` kwarg; `order_desc` controls direction.

## API Reference

::: pynteracta.api.groups.GroupsAPI
    options:
      show_source: false
      members:
        - list_groups
        - list_groups_raw
        - iterate_groups
        - list_members
        - iterate_members
        - get_for_edit
        - create
        - create_raw
        - edit
        - edit_raw
        - delete
        - edit_members
        - edit_members_bulk
        - edit_members_bulk_raw

## Facade Reference

::: pynteracta.models.facade.groups.Group

::: pynteracta.models.facade.groups.GroupList

::: pynteracta.models.facade.groups.GroupMember

::: pynteracta.models.facade.groups.GroupMemberList

::: pynteracta.models.facade.groups.GroupForEdit

::: pynteracta.models.facade.groups.GroupSummary

::: pynteracta.models.facade.groups.GroupWriteResult

::: pynteracta.models.facade.groups.GroupMembersResult

::: pynteracta.models.facade.groups.Tag
