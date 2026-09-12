# Security review — pynteracta (full source, 2026-09-11)

> **Scope:** entire `src/pynteracta/` tree (excluding the auto-generated `models/generated/`), plus
> `pyproject.toml` and `scripts/`. Read-only analysis, no diff: the review was run on a clean
> working tree at `main` (`473c476`, v0.9.0), so it covers the shipped code rather than a set of
> pending changes.
>
> **Method:** an identification pass over every source file (data-flow tracing from untrusted
> inputs — server responses, config contents, URLs, file paths — to sensitive sinks), followed by
> an independent adversarial false-positive pass on each candidate. Findings below the confidence
> bar are reported as informational notes rather than dropped, because both are concrete defects.

## Verdict

**No HIGH-severity vulnerability was found, and no finding reached the ≥ 8/10 confidence bar used
for "raise this in a PR review".**

Two concrete defects were confirmed in the token-handling path and are actionable. Both are fixed
by [`specs/v0.9.2-security-hardening.md`](specs/v0.9.2-security-hardening.md).

| # | Title | Severity | Confidence | Category |
|---|---|---|---|---|
| A | Response body/headers not redacted before hooks and audit log | Medium | 7/10 | Data exposure |
| B | Token-cache key collision across tenants | Low | 6/10 | Credential confusion |

---

## Finding A — response body and headers reach hooks and the audit log unredacted

- **File:** `src/pynteracta/transport.py:155` (capture), `:156-163` (`ResponseInfo`), `:169-178` (`audit.response`)
- **Severity:** Medium
- **Confidence:** 7/10
- **Category:** Data exposure — secret in logs and observer callbacks
- **CWE:** CWE-532 (insertion of sensitive information into log file)

### Description

`HttpTransport.request` redacts the **request** side before it leaves the transport:

```python
# transport.py:114-116
redacted_headers = redact_headers(headers)
redacted_url = redact_string(url)
req_body = redact_body(json) if (self._audit and self._audit_bodies) else None
```

The **response** side has no equivalent. The parsed body and the raw header mapping are handed
straight to both consumers:

```python
# transport.py:154-163
capture_body = self._audit and self._audit_bodies
resp_body = self._capture_response_body(response) if capture_body else None
resp_info = ResponseInfo(
    status_code=response.status_code,
    url=redacted_url,
    headers=dict(response.headers),   # not redacted
    elapsed_ms=elapsed_ms,
    request_id=request_id,
    body=resp_body,                   # not redacted
)
```

```python
# transport.py:169-178
if self._audit:
    _audit_log.debug(
        "audit.response", status=..., url=redacted_url,
        headers=dict(response.headers), ..., body=resp_body,
    )
```

The auth exchanges travel this exact path. `TokenManager._fetch_token` (`auth.py:361`) and the
Google exchange (`auth.py:436`) both call `HttpTransport.request`, and both transports are built
with the caller's audit flags:

```python
# client.py:106-119
auth_transport = HttpTransport(..., audit=audit, audit_bodies=audit_bodies)
google_exchange_transport = HttpTransport(..., audit=audit, audit_bodies=audit_bodies)
```

`_capture_response_body` returns `response.json()` (`transport.py:212-221`), so the dict
`{"accessToken": "<JWT>"}` is what lands in `ResponseInfo.body` and in the log event.

Two independent exposure channels follow:

1. **Hooks — never mitigable.** `self._hooks.on_response(resp_info)` (`transport.py:180`) passes
   the raw token to every `ClientHooks` implementation, regardless of logging configuration. The
   asymmetry is even baked into the type docstrings: `RequestInfo` says "after redaction"
   (`hooks.py:17`), `ResponseInfo` says only "Snapshot of a received HTTP response" (`hooks.py:27`).
2. **Audit log — mitigated only by a downstream step the library does not control.** Scrubbing on
   the log channel comes from `redaction_processor`, installed exclusively inside
   `setup_default_logging()` (`logging.py:200`) and `build_audit_file_handler()` (`logging.py:137`).
   By deliberate design (`logging.py:4`) the library never calls `structlog.configure()`, so a
   consumer who enables audit bodies without that call gets structlog's default renderer with no
   redaction at all.

The CLI is **not** affected: `cli/_common.py:180-188` always calls `setup_default_logging()` before
constructing the client.

Aggravating factor: `docs/logging.md:72-75` states that body keys matching `token` are redacted at
any nesting depth and that "neither channel ever receives a raw token". Only `audit_log_raw` is
documented as unsafe (`cli/__init__.py:131`, `docs/configuration.md:84`); `audit_log_bodies` is
presented as a safe opt-in. A user enabling bodies has therefore not consented to token exposure.

### Exploit scenario

An integrator wires telemetry into an APM backend:

```python
client = InteractaClient(base_url=..., credentials=key,
                         audit=True, audit_bodies=True, hooks=OtelHooks())
```

or sets `audit_log_bodies = true` in a profile while using their application's own
`structlog.configure()`. On the first request and on every subsequent token refresh, the
`audit.response` event and the `ResponseInfo.body` handed to the hook contain a valid Interacta
bearer JWT. Anyone with read access to the observability backend can replay that token against the
tenant for the remainder of its lifetime.

### Recommendation

Redact on the response side inside the transport, mirroring the request side, so the guarantee
holds independently of the consumer's structlog chain:

```python
redacted_resp_headers = redact_headers(response.headers)
redacted_resp_body = redact_body(resp_body)
```

Use those in both `ResponseInfo(...)` and the `audit.response` event. Update the `ResponseInfo`
docstring (`hooks.py:27`) to say "after redaction". Add a regression test that drives a
`create-access-token-by-service-account` response through a transport with `audit=True,
audit_bodies=True` and a capturing hook, asserting `accessToken == "***REDACTED***"` in both
channels **without** `setup_default_logging()` having been called.

Secondary: add `accesstoken` / `assertion` / `jwt` to `_SENSITIVE_KEY_RE` (`logging.py:27`). Google
`ya29.` tokens do not match the JWT shape regex and are caught today only by the key-name rule.

---

## Finding B — token-cache key collides across tenants

- **File:** `src/pynteracta/auth.py:299`; also `client.py:45-46`, `client.py:198`, `auth.py:253-257`
- **Severity:** Low
- **Confidence:** 6/10
- **Category:** Authentication — credential confusion via cache-key collision
- **CWE:** CWE-522 / CWE-706

### Description

The cache key identifies the *credential*, never the *tenant*:

```python
# auth.py:299  (service account)
self._profile: str = str(key.client_id)
```

```python
# client.py:196-199  (Google OAuth2)
return GoogleOAuth2TokenManager(google_creds, cache, google_transport,
                                cache_key=profile_name or "default")
```

All profiles share one directory by default, because `Profile.token_cache_dir` defaults to `None`:

```python
# client.py:45-46
cache_dir = profile.token_cache_dir or _default_token_cache_dir()
return FileTokenCache(cache_dir)
```

The persisted document carries no tenant marker:

```python
# auth.py:253-257
payload = {
    "access_token": token.access_token,
    "expires_at": _iso(token.expires_at),
    "obtained_at": _iso(token.obtained_at),
}
```

and `load()` (`auth.py:240-245`) validates nothing beyond those three fields. `_decode_token_expiry`
(`auth.py:468-481`) reads only `exp`, so the JWT's `iss` / `aud` are never compared against the
configured host.

Consequently two profiles pointing at different tenants whose service-account keys carry the same
`client_id` read and write the same `{client_id}.token.json`. Vendor-assigned `client_id` values are
small integers (`1001` in `docs/authentication.md:29`, `-4` in `specs/v0.1-foundation.md:299`), and
certification tenants are commonly database clones of production, so the collision is realistic
rather than contrived.

For the Google flow the library-side variant is broader: any `InteractaClient(profile=...,
google_token=...)` that omits `profile_name` writes to `default.token.json` regardless of
`base_url`. The CLI is unaffected, since it always passes the effective profile name
(`cli/_common.py:177,192`).

### Exploit scenario

A developer keeps `prod` (`https://tenant`) and `cert` (`https://cert.tenant`, a clone) profiles,
both with `client_id = 1001`. After `pynteracta --profile prod users list`, running
`pynteracta --profile cert users list` while the cached token still has more than 60 s of life
sends `Authorization: Bearer <prod token>` to the cert host (`transport.py:207-209`). The cert host
replies 401; the transport invalidates the cache and raises (`transport.py:252-258`), with no
automatic retry — but the production credential has already been transmitted. Operators, proxies,
or access logs on the less-hardened cert tenant now hold a live production bearer token.

### Recommendation

Namespace the cache key by tenant, for example `sha256(api_base)[:16] + "-" + client_id` (and
`+ profile_name` for the Google flow), and/or persist `api_base` in the cached JSON and have
`load()` discard entries whose stored base does not match the current one. Mirror the same
derivation in `cli/auth.py:289-297` (`logout`) so the command still clears the right file, and
document the on-disk layout change in `docs/authentication.md`.

---

## Informational — below the reporting bar

- **`ServiceAccountKey.__repr__` exposes the PEM.** `auth.py:136-142` is a plain `@dataclass`, so
  `repr()` renders the full private key. Nothing in the codebase reprs it; add
  `field(repr=False)` on `private_key_pem` as defence in depth.
- **`--audit-raw` audit file is created with the process umask.** `RotatingFileHandler`
  (`logging.py:147`) yields `0644`. The flag is already documented as unsafe with a loud warning,
  but `os.open(..., 0o600)` would cost nothing.
- **`setup_default_logging()` runs twice in the CLI path** (`cli/__init__.py:187` and
  `_common.py:180`), adding duplicate handlers. Noise, not a security issue.
- **`client_uid` is the only unencoded string path parameter** (`api/posts.py:459`). The caller
  already holds the token, so there is no privilege gain; `urllib.parse.quote(client_uid, safe="")`
  is a robustness improvement.

---

## Areas verified as safe

| Area | Reference | Result |
|---|---|---|
| Cross-host `Authorization` leak on redirect | `transport.py:92` | `httpx.Client(timeout=...)` leaves `follow_redirects=False` (the httpx default); no redirect is followed, so the header is never replayed to another host |
| TLS verification | `transport.py:92`, `urls.py:9-10` | No `verify=False`, no custom SSL context; `build_api_base` defaults the scheme to `https://` |
| JWT signature verification | `auth.py:468-481` | `jwt.decode(..., verify_signature=False)` is used only to read `exp` from a token the server itself issued, for cache scheduling. No authorization decision depends on it |
| Assertion signing | `auth.py:458-465` | RS512 hard-coded (no `alg` confusion, no `none`), PKCS1v15 + SHA-512, `jti=uuid4()`, 300 s TTL capped at 600 s |
| Path traversal in the token cache | `auth.py:226-228` | `/` and `\` are replaced; `"../../etc/passwd"` becomes `.._.._etc_passwd.token.json`. The service-account key is an `int` |
| Token-cache permissions | `auth.py:220-266` | `0o700` on the directory and `0o600` on the file, both verified after write; `load()` refuses to read a file with wider modes |
| Request-side redaction | `transport.py:114-123`, `logging.py:38-72` | `Authorization` blanked; `jwtAssertion` caught by the JWT-shape regex; `googleOAuth2Token` caught by the sensitive-key regex |
| Exception contents | `exceptions.py:12-27`, `transport.py:237-243` | `request_url` is redacted; `response_body` only ever holds a server error body, never a successful auth response |
| CLI output | `cli/auth.py`, `cli/_common.py:522-532` | No command prints a token; `handle_error` prints message, request id and status only; the Google token is never persisted (`cli/auth.py:188-192`) |
| `--export` destination paths | `cli/_export.py:151-159`, `:26-51` | The path comes from the local user's own CLI argument and the format is whitelisted; no server data influences it |
| YAML handling | `_common.py:223-229`, `_export.py:98-105` | `ruamel.yaml.YAML()` round-trip loader, and only `dump()` is used — no parsing of external YAML |
| TOML handling | `config.py:122`, `cli/config.py`, `cli/auth.py` | `tomllib` / `tomlkit`, data-only formats with no code-execution path |
| `subprocess` / `eval` / `exec` / `pickle` / dynamic import | whole `src/` tree | None present. `scripts/generate_models.py:139` uses `subprocess.run` with a fixed argument list, no shell, no user data |
| URL path and query parameters | `api/*.py`, `api/_utils.py:59-65` | Every path id is `int`-typed except `client_uid` (see informational note); query parameters are URL-encoded by httpx |
| `--fields` dotted-path resolution | `_common.py:318-329` | Dict and list indexing only, no `getattr` or `eval` |
| Logging side effects at import | `logging.py` | `structlog.configure()` is confined to `setup_default_logging()`; `--audit-raw` is an opt-in with a one-time warning |
| Pagination tokens | `pagination.py` | The server's `nextPageToken` is echoed back only to the same server |

## Coverage

**Read in full:** `__init__.py`, `auth.py`, `transport.py`, `config.py`, `urls.py`, `exceptions.py`,
`hooks.py`, `logging.py`, `client.py`, `pagination.py`, `api/__init__.py`, `api/_base.py`,
`api/_utils.py`, `api/auth.py`, `api/attachments.py`, `api/admin_manage.py`, `cli/__init__.py`,
`cli/_common.py`, `cli/_export.py`, `cli/auth.py`, `cli/config.py`, `models/facade/auth.py`,
`pyproject.toml`, `scripts/generate_models.py`.

**Scanned for dangerous sinks, path templates, untyped identifiers, secret handling, file I/O,
environment access and `__repr__`/`__str__` overrides (all clean):** the remaining `api/*.py`,
`cli/*.py` and `models/facade/*.py` modules.

**Excluded by instruction:** `models/generated/`, `tests/`, documentation files, and the categories
listed as out of scope for this review (denial of service, resource exhaustion, rate limiting,
secrets at rest that are already permission-protected, dependency currency).
