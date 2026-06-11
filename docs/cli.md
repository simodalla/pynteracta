# CLI Reference

## Global options

```
pynteracta [OPTIONS] COMMAND [ARGS]...

Options:
  --profile TEXT               Profile name from config file
  --config-file PATH           Override config file path
  --base-url TEXT              Interacta tenant URL
  --base-path TEXT             URL base path (default: /portal)
  --api-version INTEGER        API version (default: 2)
  --service-account-key PATH   Path to service-account key JSON
  --token-cache [file|memory]  Token cache backend
  --token-cache-dir PATH       Override token cache directory
  --timeout FLOAT              HTTP timeout in seconds
  --output [table|json|yaml]   Output format (default: table)
  --log-level [DEBUG|INFO|WARNING|ERROR]
  --no-color                   Disable rich color output
  --quiet                      Suppress non-essential output
  --audit-log                  Enable API call audit logging
  --audit-log-file PATH        Path for rotating JSON-lines audit log file
  --audit-bodies               Include request/response bodies in audit log
  --audit-raw                  Bypass redaction (unsafe — never use in production)
  --audit-max-bytes INTEGER    Max bytes per audit log file before rotation (default: 10000000)
  --audit-backups INTEGER      Number of rotated audit log files to keep (default: 5)
```

See [Audit Logging](logging.md) for full details on redaction guarantees, file format, and security considerations.

### Output format

`--output` (short: `-o`) controls the rendering format. It can be placed either **before** the
command path (global position) or **after** a data-emitting command (per-command position).
When both are supplied the command-level value wins.

```bash
# Global position (before the command path)
pynteracta --output json communities list

# Per-command position (after the command name)
pynteracta communities details 79 --output json

# Short flag works too
pynteracta communities details 79 -o yaml
```

Data-emitting commands (`auth whoami`, all `users`, `posts`, `communities`, and `catalogs`
sub-commands) accept `--output` / `-o` directly. Configuration meta-commands (`config set`,
`config get`, etc.) do not; use the global form if you need to control their output format.

### `--full` — emit all DTO fields

`--full` is a **per-command** flag available on all data-emitting commands (written after the
command, like `--web-url`). It dumps the complete field set of the underlying API DTO using
`model_dump(by_alias=True, mode="json", exclude_none=True)` — API-native camelCase keys, nested
structure preserved, null/absent fields omitted.

```bash
pynteracta users list --full --output json
pynteracta posts get 21269 --full
pynteracta communities list --full --output yaml
```

With `--output table`, `--full` switches to a **vertical per-record layout**: each record is
printed as its own key/value table (Field | Value), records visually separated. Nested values
are rendered as compact JSON inside the cell.

### `--fields <csv>` — emit selected fields

`--fields` is a **per-command** flag accepting a comma-separated list of field names in
camelCase (the keys of the full dump). Dotted paths are supported for nested values
(e.g. `attachments.0.name`, `customData.123`).

```bash
pynteracta users list --fields id,firstName,contactEmail
pynteracta posts get 21269 --output json --fields id,title,communityId
```

- **Null handling**: fields requested via `--fields` are always present in the output, even if
  their value is null (rendered as empty string in table, `null` in JSON/YAML).
- **Unknown field**: if a requested top-level field does not exist in the full dump, the command
  exits with code 2 (`EXIT_CONFIG`) and prints a message listing valid top-level keys.

### Mutual exclusion

`--full` and `--fields` cannot be used together. Providing both exits with code 2 (`EXIT_CONFIG`)
and an explanatory message.

### Interaction with `--output` and `--web-url`

`--full` / `--fields` compose with `--output` and `--web-url`:

| flags | `--output table` | `--output json/yaml` |
|-------|------------------|----------------------|
| neither | curated columns (default) | curated dict/list |
| `--full` | vertical per-record layout | complete nested dump |
| `--fields a,b` | narrow table (selected columns) | object(s) with selected keys |

When `--web-url` is set the computed URL is appended as an extra field in the output regardless
of which mode is active.

### `--export PATH` — write output to a file

`--export` is a **per-command** flag available on all data-emitting commands. It writes the
resolved data to an external file instead of printing it to the console. A one-line summary is
printed to stdout (`Wrote N records to <path> (<format>)`), suppressed by `--quiet`.

```bash
pynteracta posts list --community 79 --export posts.json
pynteracta users list --full --export users.csv
pynteracta posts get 21269 --export post.yaml
```

**Format inference** — the format is inferred from the file extension:

| Extension | Format |
|-----------|--------|
| `.csv` | CSV |
| `.json` | JSON |
| `.yaml`, `.yml` | YAML |
| `.parquet` | Parquet |

If the extension is unknown or absent use `--export-format` to specify the format explicitly:

```bash
pynteracta posts list --community 79 --export data.out --export-format csv
```

Providing an unknown extension without `--export-format` exits with code 2 (`EXIT_CONFIG`).
Providing an unknown `--export-format` value also exits with code 2. `--export-format` without
`--export` is silently ignored.

**Composition with `--full` / `--fields` / `--web-url`** — export honours all three flags with
the same semantics as console output. The file content is always driven by the export format;
`--output` does not affect the file (it controls console rendering only, and when `--export` is
set the data is not rendered to the console at all).

**Single vs list shape** — single-object commands (e.g. `posts get`, `users me`) export exactly
one record. For JSON and YAML the file contains a single object (not wrapped in an array). List
commands (e.g. `posts list`, `users list`) always export an array.

**CSV / Parquet specifics** — both formats are always row-oriented (single-object → header + 1
row). Column set = ordered union of all record keys (first-seen order). Nested values (dicts /
lists) are serialised as compact JSON strings in the cell. Missing keys in a given row → empty
cell. `None` → empty string (CSV) or `null` (Parquet).

**File creation** — existing files are overwritten (shell-redirect semantics). Missing parent
directories are created automatically.

### `--export-format {csv,json,yaml,parquet}` — explicit format override

Optional per-command flag to override the format inferred from the file extension. See
`--export` above for the full rules.

## auth

### `auth login`

Configures an authentication method for the active profile and validates it by fetching a
token. Choose **one** of the two methods (they are mutually exclusive):

**Service account** — stores the key path in the profile:

```bash
pynteracta --base-url https://interacta.example.it auth login --service-account-key sa.json
```

**Google OAuth2** — persists only `auth_method = "google_oauth2"`; the Google access token is
read from `--google-token` or `$PYNTERACTA_GOOGLE_OAUTH2_TOKEN` and is **never written to
disk**:

```bash
export PYNTERACTA_GOOGLE_OAUTH2_TOKEN="ya29.<google-access-token>"
pynteracta --base-url https://interacta.example.it auth login --google

# or pass it inline:
pynteracta --base-url https://interacta.example.it auth login --google-token "ya29.<...>"
```

| Option | Description |
|---|---|
| `--service-account-key PATH` | Use service-account auth; persists the key path. |
| `--google` | Use Google OAuth2 auth (token from `$PYNTERACTA_GOOGLE_OAUTH2_TOKEN`). |
| `--google-token TOKEN` | Google access token (implies `--google`). |
| `--profile NAME` | Profile to update (default: active profile). |

See [Authentication → Google OAuth2](authentication.md#google-oauth2) for how to obtain a
Google access token and its prerequisites.

### `auth whoami`

Prints the authenticated user's account data (calls `GET /core/auth/current-user-data`).

```bash
pynteracta auth whoami
pynteracta auth whoami --output json
```

### `auth logout`

Purges the token cache for the current profile.

```bash
pynteracta auth logout
```

## config

### `config set`

```bash
pynteracta config set base_url https://interacta.example.it
pynteracta config set service_account_key ~/keys/sa.json --profile staging
```

### `config get`

```bash
pynteracta config get base_url
```

### `config list`

```bash
pynteracta config list              # all profiles
pynteracta config list --profile staging
```

### `config use-profile`

```bash
pynteracta config use-profile staging
```

### `config add-profile`

```bash
pynteracta config add-profile staging --base-url https://staging.interacta.example.it
```

### `config remove-profile`

```bash
pynteracta config remove-profile staging
```

## users

### `users list`

Lists system users. Requires admin permissions.

```bash
pynteracta users list
pynteracta users list --all                  # paginate automatically
pynteracta users list --full-text rossi --page-size 20
pynteracta users list --all --web-url        # include web URL column
pynteracta users list --output json

# Filter by status, workspace, community (all repeatable)
pynteracta users list --status 1 --status 2
pynteracta users list --workspace 10 --community 20 --community 21
pynteracta users list --role ADMIN

# Date range (ISO-8601, epoch-ms, or datetime all accepted by the Python API)
pynteracta users list --created-from 2025-01-01 --created-to 2025-06-30

# Ordering
pynteracta users list --order-by lastName --desc
pynteracta users list --order-by lastName --asc

# Generic passthrough for long-tail string filters
pynteracta users list --filter external_id_full_text_filter=EXT-1
```

**Filter and ordering flags:**

| Flag | Description |
|---|---|
| `--full-text TEXT` | Full-text filter on name, surname, and email (`fullTextFilter`). |
| `--status INT` | Filter by user status id (`statusFilter`). Repeatable. |
| `--workspace INT` | Filter by workspace id (`workspaceIds`). Repeatable. |
| `--community INT` | Filter by community id (`communityIds`). Repeatable. |
| `--role TEXT` | Filter by role (`role`). |
| `--created-from TEXT` | Creation date lower bound (ISO-8601 string or epoch-ms integer). |
| `--created-to TEXT` | Creation date upper bound. |
| `--order-by TEXT` | Sort field id (mapped to `orderTypeId`, passthrough — no client-side validation). |
| `--desc / --asc` | Sort direction (`orderDesc`). Only sent when specified. |

**Generic passthrough (`--filter KEY=VALUE`):**

For `ListSystemUsersRequestDTO` fields not exposed as explicit flags (e.g.
`business_unit_ids`, `area_ids`, `manager_ids`, `lang`, `login_provider_filter`, name/email
prefixes), pass `KEY=VALUE`. The key is converted from `snake_case` to `camelCase`. Values are
always `str`, so list/int fields are reached via the dedicated flags above, not via `--filter`.
Repeatable.

### `users me`

Returns the **account/identity record** of the authenticated principal.
Calls `GET /core/auth/current-user-data` (`CurrentUserDataResponseDTO`).

*Use this when* you want account-level data — who is logged in, account status, account ID.

```bash
pynteracta users me
pynteracta users me --output json
```

### `users profile`

Returns the **people-directory profile** of the authenticated principal.
Calls `GET /core/user-profile/info` (`UserProfileInfoDTO`).

*Use this when* you want the richer profile fields shown in the Interacta People section —
avatar, job title, contact details, profile visibility.

```bash
pynteracta users profile
pynteracta users profile --output json
```

!!! note "me vs profile"
    `users me` and `users profile` call two different endpoints and return different data shapes.
    `me` is the identity/authentication record; `profile` is the people-directory record.

### `users get-for-edit`

Fetches a user's editable record by user ID. **Requires admin permissions on the target user.**

```bash
pynteracta users get-for-edit 5225
pynteracta users get-for-edit 5225 --web-url
```

## posts

### `posts get`

Fetches a post by ID.

```bash
pynteracta posts get 21269
pynteracta posts get 21269 --web-url --output json
```

### `posts list`

Lists posts in a community. `--community` is required.

```bash
pynteracta posts list --community 79
pynteracta posts list --community 79 --all --web-url
pynteracta posts list --community 79 --page-size 20 --output json

# Ordering
pynteracta posts list --community 79 --order-by postLastModifyAndCommentTimestamp --desc
pynteracta posts list --community 79 --order-by postTitle --asc
pynteracta posts list --community 79 --order-by postCustomField-1954 --desc --pinned-first

# Text and creator filters
pynteracta posts list --community 79 --title "Incident" --contains-text "CVE-2025"
pynteracta posts list --community 79 --created-by 101 --created-by 102

# Date range (ISO-8601, epoch-ms, or datetime all accepted by the Python API)
pynteracta posts list --community 79 --created-from 2025-01-01T00:00:00+00:00
pynteracta posts list --community 79 --created-from 2025-01-01 --created-to 2025-06-30

# Hashtag, post type, workflow filters
pynteracta posts list --community 79 --hashtag 5 --hashtag 12
pynteracta posts list --community 79 --post-type 1
pynteracta posts list --community 79 --workflow-status 3 --workflow-status 4

# Custom-field filters (COLUMN:TYPEID:VAL[,VAL])
pynteracta posts list --community 79 --field-filter 1411:4:226
pynteracta posts list --community 79 --field-filter "1954:2:1780264800000,1780955999999"
pynteracta posts list --community 79 --field-filter 1957:3:firewall

# Multiple custom-field filters
pynteracta posts list --community 79 \
    --field-filter 1411:4:226,512 \
    --field-filter 1957:3:error

# Personal and pinned filters
pynteracta posts list --community 79 --followed-by-me --only-pinned
pynteracta posts list --community 79 --to-manage

# Generic passthrough (for long-tail communityPostFilters fields)
pynteracta posts list --community 79 --filter draftType=1
```

**Ordering flags:**

| Flag | Description |
|---|---|
| `--order-by TEXT` | Sort field (see table below). |
| `--desc / --asc` | Sort direction (default: no ordering sent). |
| `--pinned-first / --no-pinned-first` | Pinned posts appear before others. |

Valid `--order-by` values: `postCustomId`, `postTitle`, `postCreatorUser`,
`postCreationTimestamp`, `postLastModifyUser`, `postLastModifyTimestamp`,
`postLastModifyAndCommentTimestamp`, `postViewedByMeTimestamp`, `postModifiedByMeTimestamp`,
`postCommentedByMeTimestamp`, `postScheduledPublication`, `postRecency`,
`postCustomField-{id}`. Invalid values exit with code 6 (`EXIT_VALIDATION`).

**Filter flags:**

| Flag | Description |
|---|---|
| `--title TEXT` | Filter by post title (partial match). |
| `--contains-text TEXT` | Full-text search across title + body. |
| `--created-by INT` | Filter by creator user ID. Repeatable. |
| `--hashtag INT` | Filter by hashtag ID. Repeatable. |
| `--post-type INT` | Filter by post type (1=CUSTOM, 2=EVENTO, 3=QUESTIONARIO). Repeatable. |
| `--workflow-status INT` | Filter by workflow status ID. Repeatable. |
| `--created-from TEXT` | Creation date lower bound (ISO-8601 string or epoch-ms integer). |
| `--created-to TEXT` | Creation date upper bound. |
| `--followed-by-me / --no-followed-by-me` | Only posts followed by the current user. |
| `--to-manage / --no-to-manage` | Only posts the current user needs to manage. |
| `--only-pinned / --no-only-pinned` | Only pinned posts. |

**Custom-field filter (`--field-filter COLUMN:TYPEID:VAL[,VAL]`):**

Format: `COLUMN_ID:TYPE_ID:VALUE[,VALUE]` — all three segments are required.

| `TYPE_ID` | Operator | `VALUE` |
|---|---|---|
| `1` | EQUAL | single value |
| `2` | INTERVAL | two epoch-ms integers (`from,to`) |
| `3` | LIKE | substring |
| `4` | IN | one or more enum/entity IDs |
| `5` | CONTAINS | single value |
| `6` | IS_NULL_OR_IN | one or more IDs |
| `7` | IS_EMPTY | (no value segment needed) |

Tokens that look like integers are coerced to `int`; others remain `str`. The flag is repeatable.

**Generic passthrough (`--filter KEY=VALUE`):**

For `communityPostFilters` fields not exposed as explicit flags, pass `KEY=VALUE`. The key is
converted from `snake_case` to `camelCase`. Values are always `str`. Repeatable.

See [Filtering and sorting posts](guides/filtering-posts.md) for a complete example-driven guide
including the Python API, custom-field discovery, builder API, and opt-in validation.

### `posts get-by-client-uid`

Fetches a post by its client UID (the `customId` field set by the API consumer).

```bash
pynteracta posts get-by-client-uid MY-UID-001
pynteracta posts get-by-client-uid MY-UID-001 --web-url --output json
```

### `posts capabilities`

Shows per-post capability flags for the authenticated principal (can view, modify, delete,
comment, like, follow, etc.).

```bash
pynteracta posts capabilities 21269
pynteracta posts capabilities 21269 --output json
```

Curated table shows the core flags (`can_view_detail`, `can_modify`, `can_delete`,
`can_view_comment`, `can_add_comment`, `can_edit_like`, `can_edit_follow`). Use `--full` to
expose all flags including `canEditComment`, `canEditWorkflowScreenData`, etc.

### `posts history`

Lists edit/event history entries for a post.

```bash
pynteracta posts history 21269
pynteracta posts history 21269 --all --page-size 50
pynteracta posts history 21269 --output json
```

### `posts global-stream`

Cross-community home feed stream. Returns posts created/modified/touched/deleted across all
communities the principal has access to.

```bash
pynteracta posts global-stream
pynteracta posts global-stream --all
pynteracta posts global-stream --sync-token <token>
```

### `posts community-list`

Lists posts in a community using the lighter `data/community-list/{communityId}` endpoint
(`ListCommunityPostsRequestDTO` — basic filters: title, description, date ranges, workflow
status, etc.).

**Distinction from `posts list`:** `posts list` calls the older `data/list/community/{communityId}`
endpoint with `ListCommunityPostsFilteredRequestDTO`, which supports additional server-side
filtering options (full-text search via `containsText`, `loadPostDetails` query flag, etc.).
Use `posts list` when you need richer filtering; use `posts community-list` for simpler requests.

```bash
pynteracta posts community-list --community 79
pynteracta posts community-list --community 79 --all --page-size 50
pynteracta posts community-list --community 79 --output json
```

### `posts check-visibility`

Checks which of the requested posts are visible to the current principal.
Pass `--with-comments` to also resolve comment visibility per post.

```bash
pynteracta posts check-visibility 21269 21270
pynteracta posts check-visibility 21269 21270 --with-comments
pynteracta posts check-visibility 21269 --output json
```

### `posts comments`

Lists comments for a post.

```bash
pynteracta posts comments 21269
pynteracta posts comments 21269 --all --output json
```

---

## `communities` commands

Retrieve community configuration settings.

### `communities list`

List all communities the authenticated principal can post in.

```bash
pynteracta communities list
pynteracta communities list --output json
```

### `communities details COMMUNITY_ID`

Show details for a single community.

```bash
pynteracta communities details 10
pynteracta communities details 10 --web-url --output json
```

### `communities details-bulk`

Retrieve details for multiple communities in one call.

```bash
pynteracta communities details-bulk --id 10 --id 20
```

### `communities post-definition COMMUNITY_ID`

Show the post structure (custom field definitions) for a community. Includes field type names from the `FieldType` enum.

```bash
pynteracta communities post-definition 10
pynteracta communities post-definition 10 --output json
```

### `communities post-definitions`

Show post definitions for multiple communities.

```bash
pynteracta communities post-definitions --id 10 --id 20
```

---

## `catalogs` commands

Retrieve post-definition catalogs and their entries.

### `catalogs list`

List all post-definition catalogs (optionally filtered by ID).

```bash
pynteracta catalogs list
pynteracta catalogs list --id 5 --id 8
pynteracta catalogs list --load-entries
```

### `catalogs entries CATALOG_ID`

List entries for a catalog. Use `--all` to paginate through all pages.

```bash
pynteracta catalogs entries 5
pynteracta catalogs entries 5 --all --page-size 50
pynteracta catalogs entries 5 --label "Eng" --order-by label --order-asc
pynteracta catalogs entries 5 --output json
```

---

## `attachments` commands

Retrieve attachment metadata, single attachment detail, and visibility checks.

> **Resource grouping note (D-v0.3-1):** All three attachment endpoints live under the
> `attachments` CLI group even though `attachments get` calls an API path under
> `communication/posts/data/attachment-detail-by-id/{id}`.  The URL prefix is a server-side
> implementation detail; the resource group is `attachments`.

> **`--web-url` is intentionally absent (D-v0.3-3b):** Bare attachments have no canonical
> deep-link URL in the Interacta web app.  `--output`, `--full`, `--fields`, and `--export`
> all compose as usual.

> **Default table = metadata only (D-v0.3-3a):** The default table shows `id`, `name`,
> `contentMimeType`, `size`, and `type`.  Short-lived `temporaryContent*Link` download and
> preview URLs are exposed only via `--full`, `--fields`, `--export`, or `--output json`.

### `attachments list`

List all attachments for a given post.

```bash
pynteracta attachments list --post 21269
pynteracta attachments list --post 21269 --all --page-size 50
pynteracta attachments list --post 21269 --output json --full
pynteracta attachments list --post 21269 --type 1 --mime-category multimedia
pynteracta attachments list --post 21269 --order-by name --order-asc
```

Filter options:

| Flag | Description |
|---|---|
| `--type INT` | Filter by attachment type (1=STORAGE, 2=DRIVE). Repeatable. |
| `--entity-type INT` | Filter by entity type (1=POST, 2=TASK, 3=COMMENT, 4=POST_FILE_PICKER, 5=SCREEN_FILE_PICKER). Repeatable. |
| `--mime-type TEXT` | Filter by MIME type string. Repeatable. |
| `--mime-category TEXT` | Filter by MIME category: `multimedia` or `other`. |
| `--order-by TEXT` | Sort field: `name`, `mimeType`, `size`, `creatorUserId`, `creationTimestamp`, `entityType`. |
| `--order-desc / --order-asc` | Sort direction (default: descending). |

Niche filters (`aiSupportedFilter`, `postFilePickerFieldId`, `wfScreenFilePickerFieldId`,
`language`) are not surfaced as CLI flags; use the Python API `list_for_post_raw(req)` for
those.

### `attachments get ATTACHMENT_ID`

Fetch a single attachment by ID.

```bash
pynteracta attachments get 3001
pynteracta attachments get 3001 --output json --full
```

The response includes the parent post's basic info (`post_id` in the curated table).
Temporary content links are accessible via `--full` or `--output json`.

### `attachments check-visibility ATTACHMENT_ID...`

Check which of the supplied attachment IDs are visible to the current principal.

```bash
pynteracta attachments check-visibility 3001 3002
pynteracta attachments check-visibility 3001 --output json
```

---

## `groups` commands

List groups, their members, and fetch group detail. `groups get` uses the
`admin/manage/groups/{groupId}/edit` endpoint (returns members + `occToken`).
`--web-url` on `groups get` deep-links to the admin group page.

### `groups list`

```bash
pynteracta groups list
pynteracta groups list --filter engineering
pynteracta groups list --order-by name --order-asc --all
pynteracta groups list --output json
```

Sort is via `order_type_id` internally; valid `--order-by` values: `name`, `email`.

### `groups members GROUP_ID`

```bash
pynteracta groups members 201
pynteracta groups members 201 --all --page-size 50
pynteracta groups members 201 --output json
```

### `groups get GROUP_ID`

```bash
pynteracta groups get 201
pynteracta groups get 201 --web-url     # includes admin group URL
pynteracta groups get 201 --output json --full
```

`occToken` is only accessible via `.raw.occToken` (propaedeutic edit token for future write use).

---

## `hashtags` commands

List hashtags for a community. Uses the admin endpoint.

### `hashtags list COMMUNITY_ID`

```bash
pynteracta hashtags list 79
pynteracta hashtags list 79 --name engineering
pynteracta hashtags list 79 --include-deleted --all
pynteracta hashtags list 79 --output json
pynteracta hashtags list 79 --export hashtags.csv
```

---

## `admin-manage` commands

Admin-only **read-form** helpers: each fetches the editable state of an entity (the
`GET admin/manage/.../edit` endpoints) together with an `occToken` for future write operations
(deferred to v1.0+). These are propaedeutic to the write surface; no write commands exist yet.

`occToken` is **not** shown in the default table — it lives on `.raw.occToken` and is reachable
via `--full`, `--output json`, or `--export` (combined with `--full`). There is no `--web-url`
flag on these commands (they are admin forms, not user-facing pages).

### `admin-manage workspace WORKSPACE_ID`

```bash
pynteracta admin-manage workspace 88
pynteracta admin-manage workspace 88 --output json --full
pynteracta admin-manage workspace 88 --fields id,name
```

Default table: `id`, `name`, `admin_users_count`, `member_users_count`, `admin_groups_count`,
`member_groups_count`. The editable `contentData` block (name/description/members) is on `.raw`.

### `admin-manage catalog CATALOG_ID`

```bash
pynteracta admin-manage catalog 5
pynteracta admin-manage catalog 5 --output json
```

Default table: `id`, `name` (i18n map), `deleted`, `community_associations_count`.

### `admin-manage catalog-entry CATALOG_ID ENTRY_ID`

```bash
pynteracta admin-manage catalog-entry 5 100
pynteracta admin-manage catalog-entry 5 100 --output json --full
```

Default table: `id`, `label` (i18n map), `external_id`, `deleted`, `parents_count`.

### `admin-manage user-credentials USER_ID`

```bash
pynteracta admin-manage user-credentials 1042
pynteracta admin-manage user-credentials 1042 --output json
```

Default table: `has_google_credentials`, `has_microsoft_credentials`, `has_custom_credentials`,
`custom_username`, `custom_active`. The full per-provider configuration is on `.raw`.

---

## `tasks` commands

Fetch task detail. A task belongs to a post (`post_id`); `--web-url` deep-links to the **parent post**, since tasks have no standalone web view (D-v0.4-3).

The default table shows curated fields: `id`, `post_id`, `title`, `state`, `priority`,
`description` (truncated `descriptionPlainText`), `attachments_count`, `creation_timestamp`.
`descriptionDelta` (Quill rich-text JSON) and survey payloads (`surveyData`,
`surveyDataCommentsInfo`) are accessible only via `--full` or `--output json` through `.raw`
(D-v0.4-4).

### `tasks get TASK_ID`

Fetch a single task by ID.

```bash
pynteracta tasks get 7001
pynteracta tasks get 7001 --output json
pynteracta tasks get 7001 --output json --full
pynteracta tasks get 7001 --web-url        # includes parent-post URL
pynteracta tasks get 7001 --fields id,title,state
pynteracta tasks get 7001 --export tasks.csv
```

**`state` vs `currentWorkflowState`:** `state` is an integer code representing the task lifecycle
(open/closed/etc.). `currentWorkflowState` is the post's workflow state DTO and is only reachable
via `.raw.currentWorkflowState` (D-v0.4-3, Q-v0.4-3).

---

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Generic CLI error (bad args, I/O) |
| 2 | Configuration error |
| 3 | Authentication error |
| 4 | Permission denied |
| 5 | Not found |
| 6 | Validation error |
| 7 | Transport error |
| 8 | Server error |
| 10 | Unexpected internal error |
