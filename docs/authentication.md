# Authentication

`pynteracta` supports two authentication methods, both yielding an Interacta access token
that is sent as `Authorization: Bearer <token>`:

- **Service account** (default) — signs a JWT assertion with an RSA key and exchanges it.
- **Google OAuth2** — signs you in with your Google account from the browser (session kept in
  the system keychain), or exchanges a Google access token you already hold.

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
from pathlib import Path

from pynteracta.auth import load_service_account_key

key = load_service_account_key(Path("sa.json"))
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
5. On HTTP 401, invalidate the cached token and raise `AuthenticationError`; the **next** call
   fetches a fresh token (there is no automatic retry of the failed request). When the server
   signals an expired token via `WWW-Authenticate: INVALID_AUTH_TOKEN`, the invalidation is logged
   as `auth.token_invalidated_by_server`.

## Google OAuth2

With the Google method you authenticate as **yourself**: your Google account must already be
**linked to an Interacta user** (ask your tenant administrator to associate it). Interacta
issues its access token in exchange for a Google access token carrying the **`email` scope**
(a token carrying only `profile` has been seen rejected with `401`, `BAD_CREDENTIALS`).

There are two ways to provide the Google access token:

- **Sign in from the browser** (recommended): `pynteracta auth login --google` runs the Google
  sign-in once, saves the session in the system keychain, and from then on the CLI and the
  library renew the Google access token on their own.
- **Static token**: you obtain a Google access token yourself and pass it each session
  (`--google-token`, `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`, `google_token` or
  `google_token_provider`).

Either way the library exchanges it with Interacta:

```
POST {base_url}/portal/api/core/auth/create-access-token-by-google-oauth2-access-token-credentials
content-type: application/json

{"googleOAuth2Token": "<Google access token>"}
```

The returned Interacta access token is cached and refreshed exactly like the service-account
flow, and sent as `Authorization: Bearer <token>`.

### Sign in from the browser

**Requirements**

- The `google` extra, which brings the system keychain support:
  ```bash
  pip install "pynteracta[google]"
  ```
- A system keychain: the macOS Keychain or the Windows Credential Manager (supported); on
  Linux the Secret Service (GNOME Keyring) or KWallet also work. Without a keychain, or with a
  backend that stores secrets in a plain file, the sign-in is refused and the static token
  remains available.
- An **OAuth client of type "Desktop app"** created by your organization (see below). Its id
  goes in the profile (`google_client_id`); its client secret is asked once and kept in the
  keychain. No OAuth client is distributed with `pynteracta`.

**First sign-in**

```bash
pynteracta --base-url https://interacta.example.it auth login --google \
  --google-client-id 000000000000-example.apps.googleusercontent.com
```

The command checks the client id, the extra and the keychain before any network call, then:

1. asks for the client secret with a hidden prompt if the keychain does not have it yet
   (`--client-secret-stdin` reads it from the first line of stdin instead, for scripts);
2. opens the Google consent page in the browser (scope `email`, PKCE) and waits up to 300
   seconds (`--login-timeout`) for the answer on a `127.0.0.1` address; the URL is printed if
   the browser does not open, and `--no-browser` prints it without opening anything;
3. exchanges the Google token with Interacta and prints `✓ Authenticated as: <name>`;
4. only then saves: in the profile `auth_method = "google_oauth2"`, the connection data and
   `google_client_id`; in the keychain the session (refresh token, the Google account email,
   the sign-in date) and the client secret.

**Using the client JSON file**

The Google Cloud console lets you download the OAuth client as a JSON file
(`client_secret_<id>.json`). Pass it with `--google-client-file` instead of
`--google-client-id` and the prompt:

```bash
pynteracta --base-url https://interacta.example.it auth login --google \
  --google-client-file ~/Downloads/client_secret_000000000000-example.apps.googleusercontent.com.json
```

The client id goes in the profile and the client secret in the keychain, as above, and only if
the sign-in succeeds; the secret from the file replaces a saved one. The path is not saved and
`pynteracta` does not modify the file: **delete it after the sign-in**, since it holds the
secret in plain text. Only "Desktop app" clients are accepted (a file with a `web` section is
refused with exit code `2`); the file cannot be combined with `--client-secret-stdin` or with a
different `--google-client-id`. From Python: `google_login.login("prod", client_file=path)`.

If any step fails (consent denied, timeout, wrong client secret, account not linked to an
Interacta user) nothing is saved. Without `--profile` the current profile of `config.toml` is
used, the same one the other commands read. A new sign-in replaces the previous session of the
profile and discards the cached Interacta token.

**Afterwards**

Every command, and `InteractaClient(profile_name=...)` from Python, uses the saved session:
when the Interacta token is missing or about to expire, the library asks Google for a new
access token with the refresh token and repeats the exchange, without opening the browser.

- The session belongs to one profile **and** one tenant: it is never used against another
  host, even if the profile's address is changed or overridden by `--base-url`.
- The client secret belongs to the OAuth client: profiles using the same `google_client_id`
  (production and certification, for example) share it and ask for it once.
- Precedence: an explicit `google_token` / `google_token_provider` wins over
  `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`, which wins over the saved session. A client built with
  only `base_url` never reads the keychain.

When the session cannot be used the library never reopens the browser by itself: it raises
`AuthenticationError` (CLI exit code `3`) asking to run `pynteracta auth login --google` again
(no session, or Google answered `invalid_grant` because the session was revoked or expired),
or to sign in again with `--replace-client-secret` (Google answered `invalid_client`, e.g. the
client secret was rotated). A network error or timeout towards Google raises `TransportError`
(exit code `7`) and leaves the session in place.

**Status, logout and revocation**

```bash
pynteracta auth status            # profile, tenant, method, session, account: no network, no secrets
pynteracta auth status --check    # also signs in and shows the identity (exit 3 if it fails)
pynteracta auth logout            # removes the cached token and the saved session (offline)
pynteracta auth logout --forget-client-secret   # also removes the client secret
pynteracta auth logout --revoke   # revokes the session at Google first, then removes it
```

!!! warning "Revocation is per account and client"
    `--revoke` withdraws the consent given to the OAuth client: it also ends the sessions of
    the same Google account with the same client on other profiles and other machines. A plain
    `auth logout` only removes the local session.

**From Python**

```python
from pynteracta import google_login
from pynteracta.client import InteractaClient

result = google_login.login(
    "prod",
    client_secret="GOCSPX-example-not-a-secret",  # omit it to use the one in the keychain
    on_auth_url=print,  # called when the browser cannot be opened
)
print(result.user_name)

with InteractaClient(profile_name="prod") as client:  # uses the saved session
    me = client.users.me()

print(google_login.status("prod").google_session)
google_login.logout("prod")
```

None of these functions writes to standard output. See the
[API reference](api/google_login.md).

**Creating the OAuth client (once per organization)**

In the Google Cloud console of your Workspace organization:

1. create (or pick) a project and configure the OAuth consent screen as **Internal**, so only
   accounts of your domain can sign in; the only scope needed is `email`;
2. create an OAuth client ID of type **Desktop app**;
3. distribute the client id (it is not a secret) and the client secret to the people who sign
   in, or the downloaded JSON file for `--google-client-file`; the secret is entered once and
   stays in each person's keychain.

**Secrets**

Refresh token and client secret live only in the system keychain, never in `config.toml`, in a
file, on the command line or in logs. The calls to the Google endpoints (token, userinfo,
revocation) appear in the audit log and reach the hooks with method, URL and status but never
with their bodies, even with `audit_log_bodies` and `audit_log_raw`. The Google account email
is shown by `auth status` only, never logged.

### Static token

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

```bash
# A base URL must be resolvable first (profile, PYNTERACTA_BASE_URL, or the global --base-url flag).
# Token from the environment (never written to disk):
export PYNTERACTA_GOOGLE_OAUTH2_TOKEN="ya29.<your-google-access-token>"
pynteracta --base-url https://interacta.example.it auth login --google --profile myprofile

# Or pass it explicitly:
pynteracta --base-url https://interacta.example.it auth login --google-token "ya29.<...>"
```

With a static token `auth login --google` persists only `auth_method = "google_oauth2"` to the
profile and does not touch the keychain; the **Google access token is never written to
`config.toml`**. Supply it each session via `PYNTERACTA_GOOGLE_OAUTH2_TOKEN` or
`--google-token`. The browser sign-in options (`--google-client-id`, `--google-client-file`,
`--client-secret-stdin`, `--replace-client-secret`, `--no-browser`, `--login-timeout`) cannot
be combined with a static token.

Any standard Google OAuth2 mechanism can mint the token, as long as it includes the `email`
scope and belongs to an Interacta-linked Google identity: the
[Google OAuth2 Playground](https://developers.google.com/oauthplayground) (select the `email`
scope and copy the access token), `gcloud auth print-access-token` with credentials carrying
the `email` scope, or your own OAuth client. Google access tokens last about one hour; when
the Interacta token derived from a static token expires, `pynteracta` re-exchanges the same
Google token, so you must provide a fresh one (e.g. via `google_token_provider`).

## Token cache

### File cache (default)

- Location: `{token_cache_dir}/{key}.token.json`, where `{key}` is
  `<sha256(api_base)[:16]>-<identity>` — the identity being the service-account `client_id` for
  the service-account flow, and the profile name for the Google OAuth2 flow.
- **The key is scoped to the tenant.** `client_id` values are vendor-assigned small integers and a
  certification tenant is often a clone of production, so two profiles pointing at different hosts
  can legitimately carry the same id. Hashing the API base into the key keeps their cache files
  distinct, so a production bearer token is never replayed against a staging host. Each cache file
  also records the `api_base` it was written for and is ignored if loaded against a different one.

!!! note "Upgrading to v0.9.3"
    The cache key changed in v0.9.3, so cache files written by earlier versions no longer match
    and each profile re-authenticates **once** on first use. Nothing needs to be cleaned up:
    the stale files are simply never read again (delete them if you want the space back). Files
    written by v0.9.2 and earlier carry no `api_base` and are still accepted by that check, so
    downgrading is not broken either.
- Default dir: `~/.config/pynteracta/tokens/` (Linux/macOS, XDG; respects `XDG_CONFIG_HOME`).
  Windows: `%LOCALAPPDATA%\pynteracta\tokens\`.
- File permissions: `0o600`; directory: `0o700`.

#### POSIX (Linux/macOS)

The library enforces `0o600` on the cache file and `0o700` on the directory. If the file mode is
anything other than `0o600` on read (e.g. world-readable), the library raises an error and refuses
to load the cached token.

#### Windows

POSIX modes (`os.chmod`) do not apply on Windows. The library emits a one-time warning (event
`token_cache.windows_permissions` on the `pynteracta.auth` logger) recommending the in-memory
cache for users who require strong at-rest protection.

### Memory cache

Tokens are kept only inside the running process — no disk write. The backend is selected on the
`Profile` (`token_cache = "memory"` in `config.toml`, `PYNTERACTA_TOKEN_CACHE=memory`, or the CLI
flag `--token-cache memory`); `InteractaClient` has no `token_cache` constructor argument.

```python
from pathlib import Path

from pynteracta.client import InteractaClient
from pynteracta.config import Profile

profile = Profile(
    base_url="https://interacta.example.it",
    service_account_key=Path("sa.json"),
    token_cache="memory",
)
client = InteractaClient(profile=profile)
```

Without a profile, a client built from `base_url=` + `credentials=` always uses the in-memory
cache.

## Authorization header

The `Authorization` header is sent as `Bearer <token>` (default `auth_scheme="Bearer"` on
`HttpTransport`). This matches the vendor-documented authentication scheme.
