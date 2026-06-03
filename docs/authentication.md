# Authentication

`pynteracta` supports two authentication methods, both yielding an Interacta access token
that is sent as `Authorization: Bearer <token>`:

- **Service account** (default) — signs a JWT assertion with an RSA key and exchanges it.
- **Google OAuth2** — exchanges a Google access token you already hold.

Select the method with the `auth_method` profile field
(`"service_account"` | `"google_oauth2"`); see [Configuration](configuration.md).

## Service-account key file

Obtain a service-account key JSON from your Interacta tenant administrator. The canonical schema
is documented in the [official vendor authentication guide](https://injenia.atlassian.net/wiki/spaces/IEAD/pages/3624075265/Autenticazione):

| Field | Type | Description |
|---|---|---|
| `type` | `string` | Must be `"service_account"` |
| `private_key_id` | `number` | Numeric ID of the signing key |
| `private_key` | `string` | RSA private key in PKCS8 PEM format |
| `client_id` | `number` | Numeric service-account identifier |

```json
{
  "type": "service_account",
  "private_key_id": 42,
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_id": 1001
}
```

Load the key in code:

```python
from pynteracta.auth import load_service_account_key

key = load_service_account_key("sa.json")
```

For integration tests, store the key at `tests/integration/.secrets/sa.json` (git-ignored). See
`tests/integration/.env.example` for the required environment variables.

## JWT assertion

`TokenManager` builds a signed JWT assertion to exchange for an access token.

### JOSE header

| Claim | Value |
|---|---|
| `alg` | `RS512` |
| `kid` | `private_key_id` (JSON number) |

### Payload

| Claim | Value |
|---|---|
| `jti` | UUID4 hex (unique per assertion) |
| `aud` | `"injenia/portal-authenticator"` (constant) |
| `iss` | `client_id` (JSON number) |
| `iat` | Current UTC epoch (seconds) |
| `exp` | `iat + 300` (vendor cap: 600 s) |

The assertion is signed with the private key using **RS512**.

## Token lifecycle

`TokenManager` handles the full JWT lifecycle transparently:

1. Build a signed RS512 JWT assertion from the SA key.
2. `POST /core/auth/create-access-token-by-service-account` with body
   `{"jwtAssertion": "<assertion>"}` to exchange it for an access token.
3. Cache the access token (file or memory backend).
4. On subsequent requests, return the cached token. Refresh it automatically when
   `now + 60 s ≥ exp` (60-second skew).
5. On HTTP 401, invalidate the cached token and re-fetch. When the server signals an expired
   token via `WWW-Authenticate: INVALID_AUTH_TOKEN`, the invalidation is logged as
   `auth.token_invalidated_by_server`.

## Google OAuth2

As an alternative to a service account, you can obtain an Interacta access token by
**exchanging a Google OAuth2 access token** that you already possess.

**Prerequisites**

- A **Google access token** with **minimum scope `profile`**.
- The Google identity behind that token must already be **linked to an Interacta user**
  (ask your tenant administrator to associate the Google account).

`pynteracta` does **not** run any Google sign-in / browser flow itself — obtaining the Google
access token is your responsibility (see *How to obtain a Google access token* below). The
library only performs the exchange:

```
POST {base_url}/portal/api/core/auth/create-access-token-by-google-oauth2-access-token-credentials
content-type: application/json

{"googleOAuth2Token": "<Google access token>"}
```

The returned Interacta access token is cached and refreshed exactly like the service-account
flow, and sent as `Authorization: Bearer <token>`.

### Library usage

```python
from pynteracta.client import InteractaClient

# Static token:
client = InteractaClient(
    base_url="https://interacta.example.it",
    google_token="ya29.<your-google-access-token>",
)

# Or supply a callable that returns a fresh Google token on demand (e.g. your own refresh
# logic). Exactly one of google_token / google_token_provider may be set.
client = InteractaClient(
    base_url="https://interacta.example.it",
    google_token_provider=lambda: get_google_access_token(),
)
```

### CLI usage

```bash
# Token from the environment (recommended — never written to disk):
export PYNTERACTA_GOOGLE_OAUTH2_TOKEN="ya29.<your-google-access-token>"
pynteracta auth login --google --profile myprofile

# Or pass it explicitly:
pynteracta auth login --google-token "ya29.<...>"
```

`auth login --google` persists only `auth_method = "google_oauth2"` to the profile; the
**Google access token is never written to `config.toml`** (it is short-lived and sensitive).
Supply it each session via `PYNTERACTA_GOOGLE_OAUTH2_TOKEN` or `--google-token`.

### How to obtain a Google access token

Any standard Google OAuth2 mechanism works, as long as the resulting access token includes
the `profile` scope and belongs to an Interacta-linked Google identity. Common options:

- **Google OAuth2 Playground** (<https://developers.google.com/oauthplayground>): select the
  `profile` (userinfo.profile) scope, authorize, and copy the **access token**. Convenient
  for quick manual testing.
- **`gcloud`**:
  ```bash
  gcloud auth login --enable-gdrive-access  # or your normal login
  gcloud auth print-access-token
  ```
  Ensure the credentials carry the `profile` / `userinfo.profile` scope.
- **Your own Google Cloud OAuth2 client**: register an OAuth client in a Google Cloud
  project and run the authorization-code (or installed-app) flow with the `profile` scope to
  mint access tokens programmatically.

Google access tokens are short-lived (typically ~1 hour). When the Interacta token derived
from it expires, `pynteracta` re-exchanges the current Google token; if the Google token has
itself expired you must provide a fresh one (e.g. via `google_token_provider`).

## Token cache

### File cache (default)

- Location: `{token_cache_dir}/{profile}.token.json`.
- Default dir: `~/.config/pynteracta/tokens/` (Linux/macOS, XDG; respects `XDG_CONFIG_HOME`).
  Windows: `%LOCALAPPDATA%\pynteracta\tokens\`.
- File permissions: `0o600`; directory: `0o700`.

#### POSIX (Linux/macOS)

The library enforces `0o600` on the cache file and `0o700` on the directory. If permissions are
wider on read (e.g. world-readable), the library raises an error and refuses to load the cached
token.

#### Windows

POSIX modes (`os.chmod`) do not apply on Windows. The library emits a one-time warning
(`pynteracta.token_cache.windows_permissions`) recommending the in-memory cache for users
who require strong at-rest protection.

### Memory cache

Tokens are kept only inside the running process — no disk write.

```python
from pynteracta.client import InteractaClient
from pynteracta.auth import load_service_account_key

key = load_service_account_key("sa.json")
client = InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
    token_cache="memory",
)
```

## Authorization header

The `Authorization` header is sent as `Bearer <token>` (default `auth_scheme="Bearer"` on
`HttpTransport`). This matches the vendor-documented authentication scheme.
