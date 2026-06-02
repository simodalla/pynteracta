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
```

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

### `posts comments`

Lists comments for a post.

```bash
pynteracta posts comments 21269
pynteracta posts comments 21269 --all --output json
```

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
