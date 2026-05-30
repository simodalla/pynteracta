# Authentication

## Service-account key

Obtain a service-account (SA) key JSON from your Interacta tenant administrator. The expected
fields are:

| Field | Type | Description |
|---|---|---|
| `clientId` | `string` | Service account identifier (also accepted as `email`) |
| `privateKey` | `string` | RSA private key in PEM format |
| `tokenAudience` | `string` | JWT audience claim — typically the tenant auth URL |
| `kid` | `string` (optional) | Key ID included in the JWT JOSE header when present |

```json
{
  "clientId": "sa-my-service@example.interacta.it",
  "privateKey": "-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----",
  "tokenAudience": "https://interacta.example.it/portal/api/external/v2/core/auth/create-access-token-by-service-account"
}
```

Load and use in code:

```python
from pynteracta.auth import load_service_account_key

key = load_service_account_key("sa.json")
```

For integration tests, store the key at `tests/integration/.secrets/sa.json` (git-ignored). See
`tests/integration/.env.example` for the required environment variables.

## Token lifecycle

`TokenManager` handles the full JWT lifecycle transparently:

1. Build a signed RS256 JWT *assertion* from the SA key.
2. `POST /core/auth/create-access-token-by-service-account` to exchange the assertion for an
   access token.
3. Cache the access token (file or memory backend).
4. On subsequent requests, return the cached token. Refresh it automatically when
   `now + 60 s ≥ exp` (60-second skew).
5. Invalidate and re-fetch on HTTP 401.

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

## Authorization header format (Q4)

The Interacta Swagger spec declares `portal_api_jwt_token` as an apiKey in the `Authorization`
header. The current provisional default sends the **raw token** (no `Bearer ` prefix).

> **Note (Q4 still pending):** Whether the raw token or `Bearer <token>` is correct has not been
> confirmed via integration testing against a production tenant. The `auth_scheme` parameter on
> `HttpTransport` allows switching to `Bearer` mode. This note will be removed once Q4 is
> confirmed.

To switch to Bearer mode explicitly:

```python
from pynteracta.transport import HttpTransport

# internal use — InteractaClient does not expose auth_scheme directly in v0.1
transport = HttpTransport(..., auth_scheme="Bearer")
```
