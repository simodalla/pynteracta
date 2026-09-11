# Filtering and sorting posts

This guide covers all the filtering and ordering capabilities of
`client.posts.list_in_community()` and `client.posts.iterate_in_community()`.

---

## Ordering

```python
from pathlib import Path

from pynteracta.auth import load_service_account_key
from pynteracta.client import InteractaClient

key = load_service_account_key(Path("sa.json"))

with InteractaClient(base_url="https://interacta.example.it", credentials=key) as client:
    # Most recently modified first (default API behavior)
    page = client.posts.list_in_community(
        56,
        order_by="postLastModifyAndCommentTimestamp",
        order_desc=True,
    )

    # Alphabetical by title, ascending
    page = client.posts.list_in_community(
        56,
        order_by="postTitle",
        order_desc=False,
    )

    # Order by a custom datetime field
    page = client.posts.list_in_community(
        56,
        order_by="postCustomField-1954",
        order_desc=True,
        pinned_first=True,  # pinned posts always appear first
    )
```

**Allowed static `order_by` values:**

| Value | Description |
|---|---|
| `postCustomId` | Custom/sequential post id |
| `postTitle` | Title |
| `postCreatorUser` | Creator user |
| `postCreationTimestamp` | Creation date |
| `postLastModifyUser` | Last modifier |
| `postLastModifyTimestamp` | Last modification date |
| `postLastModifyAndCommentTimestamp` | Last modification or comment date |
| `postViewedByMeTimestamp` | Last viewed by current user |
| `postModifiedByMeTimestamp` | Last modified by current user |
| `postCommentedByMeTimestamp` | Last commented by current user |
| `postScheduledPublication` | Scheduled publication date |
| `postRecency` | Recency score |
| `postCustomField-{id}` | Sort by custom field with given column id |

Passing an invalid value raises `ValidationError` immediately (client-side, no network call).

---

## Common filters

All filter kwargs map to fields in `communityPostFilters`. They are all optional; omit any you
don't need.

```python
from datetime import datetime, timezone

with InteractaClient(base_url="https://interacta.example.it", credentials=key) as client:
    page = client.posts.list_in_community(
        56,
        # Text filters
        title="Incident",
        description="firewall",
        contains_text="CVE-2025",

        # Creator filters
        created_by_user_ids=[101, 102],
        created_by_group_ids=[37],

        # Date range (accepts int epoch-ms, datetime, or ISO-8601 string)
        creation_timestamp_from="2025-01-01T00:00:00+00:00",
        creation_timestamp_to=datetime(2025, 6, 30, tzinfo=timezone.utc),

        # Hashtags
        hashtag_ids=[5, 12],
        hashtags_logical_and=True,   # require ALL hashtags (default: OR)

        # Post type: 1=CUSTOM, 2=EVENTO, 3=QUESTIONARIO
        post_types=[1],

        # Workflow
        current_workflow_status_ids=[3, 4],

        # Visibility: 1=PUBLIC, 2=PRIVATE (check your tenant's enum)
        visibility=1,

        # Personal filters
        followed_by_me=True,
        mentioned=True,
        to_manage=True,
        only_pinned=True,
    )
```

### Date filter formats

The `*_timestamp_from` / `*_timestamp_to` kwargs accept three equivalent forms:

```python
# epoch-milliseconds int
creation_timestamp_from=1735689600000

# datetime object (naive → UTC assumed)
from datetime import datetime, timezone
creation_timestamp_from=datetime(2025, 1, 1, tzinfo=timezone.utc)

# ISO-8601 string
creation_timestamp_from="2025-01-01T00:00:00+00:00"
```

---

## Custom-field filters

Custom fields are filtered via `post_field_filters` (or `screen_field_filters` for workflow
screen fields). Each entry requires three values:

- `column_id` — the field's numeric id (from the community's post-definition)
- `type_id` — the filter operator (see `FilterType` enum)
- `parameters` — a list of values whose type depends on `type_id`

### FilterType values

| `FilterType` | int | `parameters` |
|---|---|---|
| `EQUAL` | 1 | `[value]` |
| `INTERVAL` | 2 | `[from_epoch_ms, to_epoch_ms]` |
| `LIKE` | 3 | `["substring"]` |
| `IN` | 4 | `[id1, id2, ...]` |
| `CONTAINS` | 5 | `[value]` |
| `IS_NULL_OR_IN` | 6 | `[id1, ...]` |
| `IS_EMPTY` | 7 | `[]` |

### Field type → operator mapping (confirmed)

| Field type | Recommended `FilterType` |
|---|---|
| ENUM, ENUM_LIST, HIERARCHICAL_ENUM, GENERIC_ENTITY_LIST | `IN` |
| DATE, DATETIME | `INTERVAL` |
| STRING, TEXT_AREA, DELTA_AREA | `LIKE` |

### Building filters by id

```python
from pynteracta.models.facade.post_filters import FilterType, PostFieldFilter

with InteractaClient(base_url="https://interacta.example.it", credentials=key) as client:
    page = client.posts.list_in_community(
        56,
        post_field_filters=[
            # ENUM field "Tipologia" IN [226 "Manutenzione sistemistica"]
            PostFieldFilter(column_id=1411, type_id=FilterType.IN, parameters=[226]),
            # DATETIME field "Data e ora inizio" in a date range
            PostFieldFilter(
                column_id=1954,
                type_id=FilterType.INTERVAL,
                parameters=[1780264800000, 1780955999999],
            ),
            # DELTA_AREA field "Causa" LIKE substring
            PostFieldFilter(column_id=1957, type_id=FilterType.LIKE, parameters=["firewall"]),
        ],
    )
```

Raw dicts are also accepted (both `camelCase` and `snake_case` keys):

```python
post_field_filters=[
    {"columnId": 1411, "typeId": 4, "parameters": [226]},
]
```

---

## Discovering fields: the post-definition

To find the `column_id` values for your community and the allowed enum `parameters`, fetch the
community's post-definition (already exposed in v0.1.0):

```python
pd = client.communities.post_definition(56)

for fd in pd.field_definitions:
    if not fd.searchable:
        continue
    print(f"{fd.id:5}  {fd.type.name if fd.type else '?':20}  {fd.label}")
    for ev in fd.enum_values:
        status = " [deleted]" if ev.deleted else ""
        print(f"         {ev.id:6}  {ev.label}{status}")
```

Example output:

```
 1411  ENUM                 Tipologia
          226  Manutenzione sistemistica (aggiornamenti software, ecc..)
          512  Modifica configurazioni (firewall, console amministrative..)
           28  Generica
           26  Progetto [deleted]
 1954  DATETIME             Data e ora inizio
 1957  DELTA_AREA           Causa
```

---

## Building filters by label

`PostFieldFilterBuilder` resolves field `externalId` or `label` to `column_id`, and enum value
`label` to its numeric `id`, so you don't need to know the ids upfront.

```python
from pynteracta.models.facade.post_filters import PostFieldFilterBuilder, FilterType

pd = client.communities.post_definition(56)
builder = PostFieldFilterBuilder(pd)

page = client.posts.list_in_community(
    56,
    post_field_filters=[
        # By field externalId + enum value label
        builder.build("assegnatario", [3872]),          # externalId "assegnatario" = col 1415
        builder.build("Tipologia", ["Generica"]),        # label resolves to id 28
        builder.build("Tipologia", ["Manutenzione sistemistica (aggiornamenti software, ecc..)"]),

        # By field label + explicit type_id override
        builder.build("Data e ora inizio",
                      [1780264800000, 1780955999999],
                      type_id=FilterType.INTERVAL),

        # By numeric column_id (type inferred from field type)
        builder.build(1957, ["firewall"]),
    ],
)
```

**Resolution rules:**

- `externalId` is preferred over `label` — use it when available (stable, unambiguous).
- Deleted enum values are **excluded by default**. Pass `include_deleted=True` to the builder
  constructor to include them.
- Duplicate labels raise `ValidationError` — use the numeric id directly in that case.

---

## Opt-in validation

Pass `validate_with=` to validate custom-field filters against the post-definition before the
network call. If a `column_id` doesn't exist or a parameter id is not a valid enum value,
`ValidationError` is raised immediately (no API request is made).

```python
pd = client.communities.post_definition(56)

# This raises ValidationError immediately if column_id 9999 isn't in the post-definition
page = client.posts.list_in_community(
    56,
    post_field_filters=[
        PostFieldFilter(column_id=9999, type_id=FilterType.IN, parameters=[1]),
    ],
    validate_with=pd,
)
```

What `validate_with` checks:

1. Each `column_id` exists in the community's field definitions.
2. For enum fields (ENUM / ENUM_LIST / HIERARCHICAL_ENUM), every `parameters` id is a valid
   (non-deleted, by default) enum value.
3. The `type_id` is compatible with the field's type for confirmed pairings (e.g., using `LIKE`
   on an ENUM field raises an error). Unconfirmed field types are skipped (permissive).

The CLI equivalent is `posts list --validate`, which performs the post-definition lookup for you
and applies the same checks to `--field-filter` and `--screen-field-filter` (exit code 6 on
failure):

```bash
pynteracta posts list --community 56 --field-filter 1411:4:226 --validate
```

---

## Escape hatches

### Pre-built `community_post_filters` dict

For long-tail fields not promoted to explicit kwargs (e.g. `eventPostFilter`,
`acknowledgeTaskFilter`, `draftType`), pass a raw dict:

```python
client.posts.list_in_community(
    56,
    community_post_filters={
        "eventPostFilter": {"startDateFrom": 1780264800000},
        "draftType": 1,
    },
)
```

Explicit kwargs and `community_post_filters` are merged; explicit kwargs take precedence for
overlapping keys.

### `**filters` passthrough (Python API)

Any additional keyword argument is camelCased and added to the **top-level** request body
(not to `communityPostFilters`):

```python
client.posts.list_in_community(56, calculate_total_items_count=True)
```

> **CLI note:** `--filter KEY=VALUE` maps to `community_post_filters`, not to the top-level body.

### `list_in_community_raw()`

Pass a fully pre-built `ListCommunityPostsFilteredRequestDTO`:

```python
from pynteracta.models.facade.posts import ListCommunityPostsFilteredRequestDTO

req = ListCommunityPostsFilteredRequestDTO(
    orderBy="postTitle",
    pageSize=50,
)
client.posts.list_in_community_raw(56, req)
```

---

## Pagination

```python
# Single page
page = client.posts.list_in_community(56, order_by="postTitle", page_size=50)
for post in page.items_typed:
    print(post.title)

# All pages lazily
for post in client.posts.iterate_in_community(
    56,
    order_by="postCreationTimestamp",
    order_desc=False,
    post_types=[1],
    page_size=100,
):
    print(post.title)
```

All kwargs accepted by `list_in_community` are also accepted by `iterate_in_community`.
