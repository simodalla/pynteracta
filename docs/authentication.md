# Authentication

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

## Token cache

### File cache (default)

- Location: `{token_cache_dir}/{profile}.token.json`.
- Default dir: `platformdirs.user_cache_dir("pynteracta")`.
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
