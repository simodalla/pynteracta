# Groups API

The `GroupsAPI` client exposes three read endpoints added in v0.5.0.

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
    print(group.raw.occToken)  # occToken only on .raw — for future write use
```

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

## Facade Reference

::: pynteracta.models.facade.groups.Group

::: pynteracta.models.facade.groups.GroupList

::: pynteracta.models.facade.groups.GroupMember

::: pynteracta.models.facade.groups.GroupMemberList

::: pynteracta.models.facade.groups.GroupForEdit

::: pynteracta.models.facade.groups.Tag
