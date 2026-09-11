# Filtering and sorting users

This guide covers the filtering and ordering capabilities of `client.users.list()` and
`client.users.iterate()` (endpoint `POST admin/data/users`, admin permissions required), and
their CLI equivalents on `pynteracta users list`. It mirrors the
[posts guide](filtering-posts.md).

---

## Ordering

```python
from pynteracta import InteractaClient

with InteractaClient.from_service_account("sa.json") as client:
    # Sort by a field id, descending
    page = client.users.list(order_by="lastName", order_desc=True)

    # Ascending
    page = client.users.list(order_by="lastName", order_desc=False)
```

`order_by` maps to the request field `orderTypeId`; `order_desc` maps to `orderDesc`. Unlike
posts, the users endpoint has **no published list of sort field ids**, so `order_by` is passed
through without client-side validation (decision Q-v0.8-2). An unknown value is rejected by the
server with a `ValidationError` (HTTP 400).

CLI:

```bash
pynteracta users list --order-by lastName --desc
pynteracta users list --order-by lastName --asc
```

---

## Curated filters

All filter kwargs are optional and map 1:1 onto `ListSystemUsersRequestDTO` fields.

```python
from datetime import datetime, timezone

with InteractaClient.from_service_account("sa.json") as client:
    page = client.users.list(
        # Full-text on first name, last name and email
        full_text_filter="rossi",

        # Status ids (tenant-specific enum), workspaces, communities
        status_filter=[1, 2],
        workspace_ids=[10],
        community_ids=[20, 21],

        # Role
        role="ADMIN",

        # Creation date range (epoch-ms int, datetime, or ISO-8601 string)
        creation_timestamp_from="2025-01-01T00:00:00+00:00",
        creation_timestamp_to=datetime(2025, 6, 30, tzinfo=timezone.utc),

        # Last-access date range — "who has not logged in since …"
        last_access_timestamp_to="2026-01-01",
    )
```

| kwarg | Request field | CLI flag |
|---|---|---|
| `full_text_filter` | `fullTextFilter` | `--full-text TEXT` |
| `status_filter` | `statusFilter` | `--status INT` (repeatable) |
| `workspace_ids` | `workspaceIds` | `--workspace INT` (repeatable) |
| `community_ids` | `communityIds` | `--community INT` (repeatable) |
| `role` | `role` | `--role TEXT` |
| `creation_timestamp_from` / `_to` | `creationTimestampFrom` / `To` | `--created-from` / `--created-to` |
| `last_access_timestamp_from` / `_to` | `lastAccessTimestampFrom` / `To` | `--last-access-from` / `--last-access-to` |
| `order_by` | `orderTypeId` | `--order-by TEXT` |
| `order_desc` | `orderDesc` | `--desc` / `--asc` |

### Date filter formats

The four `*_timestamp_*` kwargs accept the same three forms as the posts API:

```python
creation_timestamp_from=1735689600000                                   # epoch-ms int
creation_timestamp_from=datetime(2025, 1, 1, tzinfo=timezone.utc)       # datetime (naive → UTC)
creation_timestamp_from="2025-01-01T00:00:00+00:00"                     # ISO-8601 string
```

On the CLI both ISO-8601 strings and epoch-ms integers are accepted:

```bash
pynteracta users list --created-from 2025-01-01 --created-to 2025-06-30
pynteracta users list --last-access-to 1767225600000
```

---

## Escape hatches

### `**filters` passthrough (Python API)

Any additional keyword argument is camelCased and added to the request body. Use it for the
long-tail `ListSystemUsersRequestDTO` fields not promoted to explicit kwargs, for example
`business_unit_ids`, `area_ids`, `manager_ids`, `lang`, `login_provider_filter`,
`people_section_enabled`, `reduced_profile`, or the `*_prefix_full_text_filter` family:

```python
client.users.list(
    business_unit_ids=[3],
    login_provider_filter=[2],
    email_prefix_full_text_filter="m.",
)
```

Explicit kwargs and `**filters` are merged into a single body; a `None` explicit kwarg is dropped.

### CLI `--filter KEY=VALUE`

The CLI passthrough converts `snake_case` keys to `camelCase` and types the value:
`true`/`false` become booleans, integer literals become integers, everything else stays a
string. List-valued fields (`business_unit_ids`, `login_provider_filter`, …) cannot be expressed
with `--filter`; use the dedicated repeatable flags where they exist.

```bash
pynteracta users list --filter external_id_full_text_filter=EXT-1
pynteracta users list --filter reduced_profile=false --filter place=Bologna
```

### `list_raw()`

Pass a fully pre-built `ListSystemUsersRequestDTO`:

```python
from pynteracta.models.generated.external_v2 import ListSystemUsersRequestDTO

req = ListSystemUsersRequestDTO(fullTextFilter="rossi", pageSize=50, orderTypeId="lastName")
page = client.users.list_raw(req)
```

---

## Pagination and counting

```python
# Single page
page = client.users.list(page_size=50, status_filter=[1])
for user in page.items_typed:
    print(user.id, user.firstName, user.lastName, user.contactEmail)
print(page.next_page_token)   # None on the last page

# Resume from a token
page2 = client.users.list(page_size=50, status_filter=[1], page_token=page.next_page_token)

# All pages lazily — every list() kwarg is accepted by iterate()
for user in client.users.iterate(page_size=100, status_filter=[1]):
    print(user.id)

# Just the total
total = client.users.list(page_size=1, calculate_total_items_count=True).total_items_count
```

CLI:

```bash
pynteracta users list --status 1 --page-size 50          # one page; next token on stderr
pynteracta users list --status 1 --page-token <TOKEN>    # resume
pynteracta users list --status 1 --all                   # every page
pynteracta users list --status 1 --count                 # prints only the total
```

See the [CLI reference](../cli.md#users-list) for the complete flag list, output modes and
export options.
