# Code Review — M5 (Resource clients, pagination, `InteractaClient`)

Review date: 2026-05-29

Overall the structure is sound: dual transports avoid recursive token fetch, resource clients match the §8 endpoint catalog, and respx tests cover the happy paths. The issues below are ordered by severity.

---

## High

### 1. `PageIterator` can loop forever on a broken API page

```56:71:src/pynteracta/pagination.py
    def __next__(self) -> T:
        while True:
            ...
            page = self._fetch_page(self._token)
            self._items = self._items_getter(page)
            ...
            self._token = self._token_getter(page)
            if not self._token:
                self._done = True
            if self._index >= len(self._items) and self._done:
                raise StopIteration
```

If the API returns **empty `items` but a non-empty `nextPageToken`**, `_done` stays `False` and the loop never terminates. That can happen with a buggy server, a mismatched schema, or a filter that yields no rows but still paginates.

**Missing test:** empty page + non-empty token (should stop or raise, not spin).

---

### 2. `InteractaClient` bypasses config/env when `base_url` is passed explicitly

```76:77:src/pynteracta/client.py
        if credentials is not None:
            cache = _build_token_cache(profile) if profile is not None else MemoryTokenCache()
```

A common pattern is:

```python
InteractaClient(base_url="...", credentials=load_service_account_key(...))
```

In that case **`PYNTERACTA_TOKEN_CACHE=file` and `token_cache_dir` are ignored** — cache is always in-memory. The plan's 4-level config precedence (defaults < file < env < CLI) is only partially wired: `resolve_profile()` runs only when *both* `profile` and `base_url` are omitted.

**Missing test:** client constructed with explicit `base_url` + credentials still respects env/file token-cache settings (or documents that it won't).

---

## Medium

### 3. Non-dict JSON responses raise `TypeError`, not `InteractaError`

```17:23:src/pynteracta/api/_base.py
    def _get(self, path: str, *, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._transport.request("GET", path, params=params)
        body: Any = response.json()
        if not isinstance(body, dict):
            ...
            raise TypeError(msg)
```

Callers expecting the §10 hierarchy (`ValidationError`, `AuthenticationError`, etc.) from all API failures will get an uncategorized `TypeError` on unexpected response shapes (e.g. bare string error body on 200). Same in `AuthAPI.create_access_token_raw`.

---

### 4. `PageIterator` is single-use; a second pass yields nothing

`__iter__` returns `self` without resetting `_done`, `_token`, or `_index`. After one full consumption, `list(iterator)` is empty. That may be intentional, but it's surprising for users who treat iterators as reusable factories (as `client.users.iterate(...)` suggests).

**Missing test:** second iteration behavior (document or reset).

---

### 5. `posts.get()` always sends explicit `false` query flags

`build_query_params` omits only `None`, not `False`. With all defaults, every `loadMainAttachment*` flag is sent as `false`. If the API treats "absent" and "false" differently (common for optional booleans), behavior may diverge from omitting unset flags.

**Missing test:** default `get()` query string is empty vs explicit falses (confirm against real API).

---

### 6. Bare `InteractaClient()` can fail with an opaque `KeyError`

```56:57:src/pynteracta/client.py
        if profile is None and base_url is None:
            profile = resolve_profile(profile_name=profile_name, config_file=config_file)
```

With no config file and no env `PYNTERACTA_BASE_URL`, this surfaces as `KeyError` from `resolve_profile`, not a clear `ValueError` like the explicit `base_url` branch. CLI/M6 callers may hit this often.

---

## Low / design gaps

### 7. `AuthAPI.create_access_token_raw` footgun when used outside `InteractaClient`

If constructed as `AuthAPI(make_transport(token_provider=...))` without `unauthenticated_transport`, the SA assertion call will include a bearer token. `InteractaClient` wires this correctly; standalone use is easy to get wrong. Worth a stronger doc warning or a constructor guard.

### 8. `PageLike` is unused dead code

Defined in `pagination.py` but nothing implements or checks it. Harmless, but adds noise.

### 9. `InteractaClient` not exported from `pynteracta`

```5:5:src/pynteracta/__init__.py
__all__ = ["__version__"]
```

Library consumers must import from `pynteracta.client`. Fine for v0.1 alpha, but differs from typical client-library ergonomics.

### 10. Plan deviation: no injectable `httpx.Client`

§8 shows `http_client: httpx.Client | None = None`; not implemented. Two separate `HttpTransport` instances also mean two connection pools when credentials are set.

---

## Missing tests (acceptance gaps vs plan)

| Area | Covered? | Gap |
|------|----------|-----|
| All §8 endpoints (happy path) | Yes | — |
| Pagination stop on empty token | Yes | — |
| Pagination error propagation | Partial | Only via generic `NotFoundError` in `test_pagination.py`; not through `users.iterate` / API layer |
| 401 → cache invalidation | M4 transport + M4 auth | **Not wired through `InteractaClient`** |
| Web URL trailing-slash invariants | M1 `test_urls.py` | No regression via `client.web_urls` beyond one smoke assert |
| `FileTokenCache` via client + profile | No | — |
| Invalid pydantic filter kwargs | No | `list(full_text_filter=...)` with bad types |
| `create_access_token` via `client.auth` | No | Only direct `AuthAPI` test |

---

## Security

No new critical issues. Existing M4 guarantees hold (dual transport for SA exchange, redaction in transport). Minor note: `**filters: Any` accepts arbitrary body keys — callers can accidentally send fields the API doesn't expect, but that's caller responsibility, not a library vulnerability.

---

## Summary

The M5 skeleton is in good shape and tests pass, but **#1 (infinite pagination loop)** and **#2 (token-cache config bypass)** should be addressed before calling this merge-ready for real tenant use. **#3–#6** are worth fixing or documenting before M6 CLI builds on these APIs.
