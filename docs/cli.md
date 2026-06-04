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
```

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
```

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
