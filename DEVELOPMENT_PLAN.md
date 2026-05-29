# `pynteracta` — Development Plan (v0.1)

> Unofficial third-party Python client (library + CLI) for the **Interacta™** platform by Dinova S.r.l. / Maggioli S.p.A. Neither sponsored nor endorsed by the vendor.

---

## 1. Overview and Objectives

`pynteracta` is a Python 3.12+ library and CLI providing a Pythonic, type-safe interface to the Interacta REST API (`external_v2`). The first release (**v0.1**) is intentionally narrow in scope and emphasizes **robustness, observability and testability** over feature breadth, because:

- The Interacta API is owned by a third party and may change without notice.
- The library is expected to be used in long-running automations where silent breakage is unacceptable.

### In scope for v0.1
- Service-account authentication, JWT lifecycle and caching.
- **Read-only** access to: auth/identity, users (4 endpoints), posts (3 endpoints).
- Library API + Typer-based CLI.
- 4-level configuration (defaults → file → env → CLI), multi-profile.
- Hybrid pydantic v2 models (generated baseline + ergonomic façade).
- Structured logging with redaction.
- Comprehensive testing (unit/contract/integration/snapshot).
- Self-hosted GitLab CI; v0.x wheel distributed as a GitLab artifact only.

### Out of scope for v0.1 (future roadmap)
- All mutations (create/edit/delete) on posts, users, comments, groups, etc.
- Tasks, attachments upload/download, admin manage beyond `getUserForEdit`, workspaces, catalogs, hashtags, surveys.
- Google OAuth2 authentication.
- Automatic retry/backoff.
- Async API (`AsyncInteractaClient` planned for v0.3+).
- Public PyPI publication (planned for v1.0 once the API surface stabilizes).

### Non-goals
- No mocking of the Interacta web UI.
- No support for self-hosted/on-prem variants other than what differs by `base_url` + `base_path`.

---

## 2. Technology Stack (decided)

| Concern | Choice |
|---|---|
| Python | 3.12, 3.13 (test matrix) |
| HTTP client | `httpx` (sync only in v0.1) |
| Models | `pydantic` v2 |
| CLI | `typer` |
| CLI rendering | `rich` |
| Logging | `structlog` |
| Packaging | `uv` + `pyproject.toml` (PEP 621) |
| Lint/format | `ruff` (check + format) |
| Typing | `mypy --strict` |
| Tests | `pytest`, `respx`, `syrupy`, `pytest-cov` |
| Model generation | `datamodel-code-generator` |
| Docs | `mkdocs-material` + `mkdocstrings[python]` |
| Changelog | `git-cliff` |
| Versioning/release | `python-semantic-release` |
| Config dirs | `platformdirs` |
| TOML | `tomllib` (stdlib) read; `tomli-w` write |

---

## 3. Project Structure and Module Responsibilities

```
pynteracta/
├── pyproject.toml
├── README.md
├── LICENSE                       # Apache-2.0
├── CHANGELOG.md
├── .gitignore
├── .pre-commit-config.yaml
├── .gitlab-ci.yml
├── cliff.toml
├── mkdocs.yml
├── src/
│   └── pynteracta/
│       ├── __init__.py           # public re-exports + __version__
│       ├── client.py             # InteractaClient façade
│       ├── auth.py               # ServiceAccountCredentials, TokenManager, TokenCache
│       ├── config.py             # Config, Profile, loader (defaults<file<env<flags)
│       ├── exceptions.py         # error hierarchy
│       ├── transport.py          # httpx wrapper, request/response logging, redaction
│       ├── logging.py            # structlog setup, processors, redactor
│       ├── pagination.py         # PageIterator helper
│       ├── urls.py               # URL normalization + WebUrls helper
│       ├── models/
│       │   ├── __init__.py       # re-exports the façade models
│       │   ├── generated/        # AUTO-GENERATED, do NOT hand-edit
│       │   │   └── external_v2.py
│       │   └── facade/           # hand-written ergonomic wrappers
│       │       ├── auth.py
│       │       ├── users.py
│       │       └── posts.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── _base.py          # ResourceClient base
│       │   ├── auth.py           # AuthAPI
│       │   ├── users.py          # UsersAPI
│       │   └── posts.py          # PostsAPI
│       └── cli/
│           ├── __init__.py       # typer root app, global options
│           ├── _common.py        # output formatting, error renderer
│           ├── auth.py
│           ├── config.py
│           ├── users.py
│           └── posts.py
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   │   ├── conftest.py
│   │   └── .secrets/             # gitignored
│   └── fixtures/
│       └── swagger.json          # pinned snapshot used by contract tests
├── docs/
│   ├── index.md
│   ├── quickstart.md
│   ├── configuration.md
│   ├── authentication.md
│   ├── urls.md
│   ├── cli.md
│   └── api/                      # mkdocstrings-rendered
└── scripts/
    └── generate_models.py
```

### Module roles
- `client.py`: top-level `InteractaClient` façade aggregating `auth`, `users`, `posts`, `web_urls`.
- `auth.py`: credentials parsing, JWT lifecycle, file cache (mode 0o600) or in-memory cache.
- `transport.py`: `HttpTransport` wraps `httpx.Client`, injects `Authorization`, custom `User-Agent`, request/response hooks, error mapping.
- `api/_base.py`: shared `ResourceClient` (URL build, body validation, error translation).
- `models/generated/`: untouched output of `datamodel-code-generator`.
- `models/facade/`: hand-written, narrower, ergonomic versions for the in-scope endpoints; expose only the fields we actually use in v0.1.

---

## 4. Configuration System

### Data model (pydantic v2)

```python
class Profile(BaseModel):
    base_url: HttpUrl
    base_path: str = "/portal"
    api_version: int = 2
    service_account_key: Path | None = None
    token_cache: Literal["file", "memory"] = "file"
    token_cache_dir: Path | None = None          # default: platformdirs.user_cache_dir
    timeout_seconds: float = 30.0
    log_level: Literal["DEBUG","INFO","WARNING","ERROR"] = "INFO"

class Config(BaseModel):
    current_profile: str = "default"
    profiles: dict[str, Profile]
```

### File location
- Path: `platformdirs.user_config_dir("pynteracta") / "config.toml"`.
- Linux example: `~/.config/pynteracta/config.toml`.
- TOML schema:
  ```toml
  current_profile = "dev"

  [profiles.dev]
  base_url        = "https://interacta.example.it"
  base_path       = "/portal"
  api_version     = 2
  service_account_key = "~/.config/pynteracta/sa-dev.json"

  [profiles.prod]
  base_url        = "https://interacta.unionerenolavinosamoggia.bo.it"
  service_account_key = "~/.config/pynteracta/sa-prod.json"
  ```

### Precedence (highest wins)
1. CLI flag
2. Environment variable (`PYNTERACTA_*`)
3. Config file profile (selected by `--profile`/`PYNTERACTA_PROFILE`/`current_profile`)
4. Built-in defaults

### Environment variables
| Var | Maps to |
|---|---|
| `PYNTERACTA_PROFILE` | active profile name |
| `PYNTERACTA_BASE_URL` | `base_url` |
| `PYNTERACTA_BASE_PATH` | `base_path` |
| `PYNTERACTA_API_VERSION` | `api_version` |
| `PYNTERACTA_SERVICE_ACCOUNT_KEY` | `service_account_key` |
| `PYNTERACTA_TOKEN_CACHE` | `token_cache` |
| `PYNTERACTA_TOKEN_CACHE_DIR` | `token_cache_dir` |
| `PYNTERACTA_TIMEOUT` | `timeout_seconds` |
| `PYNTERACTA_LOG_LEVEL` | `log_level` |
| `PYNTERACTA_CONFIG_FILE` | override config file path |

### CLI global flags (resolved before any command)
`--profile`, `--base-url`, `--base-path`, `--api-version`, `--service-account-key`, `--output`, `--log-level`, `--config-file`.

### `pynteracta config` commands
- `set <key> <value> [--profile NAME]`
- `get <key> [--profile NAME]`
- `list [--profile NAME]` (no profile → list all profiles)
- `use-profile <name>` (sets `current_profile`)
- `add-profile <name> --base-url ...`
- `remove-profile <name>`

---

## 5. URL Construction

### API URLs (3 parametric components)
```
{base_url}{base_path}/api/external/v{api_version}/{endpoint}
```

### Normalization rules (`urls.build_api_base`)
1. Strip whitespace.
2. Ensure `base_url` has scheme (default `https://`) if user passed bare host.
3. Strip trailing `/` from `base_url`.
4. If `base_path` is empty → use `""`; else ensure it starts with `/` and has no trailing `/`.
5. Join with single `/` between segments.

Test vectors (must all produce the same canonical base `https://host/portal/api/external/v2`):
- `("https://host", "/portal", 2)`
- `("https://host/", "portal", 2)`
- `("host", "/portal/", 2)`
- `("https://host//", "//portal//", 2)`

### Web URL patterns
Reproduced verbatim (preserve trailing slashes):
- Post: `{base_url}{base_path}/post/{postId}`
- User: `{base_url}{base_path}/admin/user/{userId}/`
- Community: `{base_url}{base_path}/community/{communityId}`

### Public API
```python
class WebUrls:
    def post(self, post_id: int) -> str: ...
    def user(self, user_id: int) -> str: ...
    def community(self, community_id: int) -> str: ...
```
Exposed as `client.web_urls`.

---

## 6. Authentication

### Service Account flow
1. Read SA key file (JSON) — schema TBD (**Open question Q1**); presumed fields: `kid`, `email`/`clientId`, `privateKey` (PEM), `tokenAudience`.
2. Build a signed JWT *assertion* (algorithm TBD — likely RS256; **Open question Q2**).
3. `POST /core/auth/create-access-token-by-service-account` with body `CreateAccessTokenByServiceAccountRequestDTO`.
4. Receive `CreateAccessTokenByServiceAccountResponseDTO` → contains the access token (JWT) and presumably `expiresIn` (**Open question Q3**).
5. Cache token; attach as `Authorization: <token>` header (Swagger spec defines security scheme `portal_api_jwt_token` as apiKey in `Authorization`; whether it expects raw token vs `Bearer <token>` prefix → **Open question Q4**).

### `TokenManager` responsibilities
- `get_token() -> str`: returns valid token, refreshing if `now + skew >= expires_at` (skew = 60 s).
- Thread-safe (single `threading.Lock`).
- Pluggable `TokenCache` backend: `FileTokenCache` (default) or `MemoryTokenCache`.

### Token cache file
- Location: `{token_cache_dir}/{profile}.token.json`.
- Content: `{ "access_token": "...", "expires_at": "<ISO8601 UTC>", "obtained_at": "..." }`.
- File created with mode `0o600`; directory `0o700`.
- On startup, verify mode; if wider, refuse to read and warn.

### Security
- Never log SA private key, raw assertion, or access token (see Redaction in §12).
- Memory mode: token kept only inside the process.

### Indicative interfaces
```python
@dataclass(frozen=True)
class ServiceAccountKey:
    client_id: str
    private_key_pem: str
    # TBD additional fields

class TokenManager:
    def __init__(self, transport: HttpTransport, key: ServiceAccountKey,
                 cache: TokenCache, clock: Callable[[], datetime] = utcnow): ...
    def get_token(self) -> str: ...
    def invalidate(self) -> None: ...
```

---

## 7. Models Strategy (Hybrid)

### Generated baseline
- Tool: `datamodel-code-generator --input swagger.json --input-file-type openapi --output-model-type pydantic_v2.BaseModel --use-annotated --use-standard-collections --use-union-operator --target-python-version 3.12 --output src/pynteracta/models/generated/external_v2.py`.
- Committed to the repo for reproducibility and PR diffs.
- Module is fully regenerated by `scripts/generate_models.py`; never hand-edited.

### Façade models (hand-written)
- One file per resource in `models/facade/`.
- Re-export only the **fields actually used** by v0.1 (narrower, better documented).
- Use composition: `class Post(BaseModel): raw: generated.GetPostDetailResponseDTO`, with computed properties for ergonomics.
- Forward-compatibility: unknown fields ignored (`model_config = ConfigDict(extra="ignore")`).

### Regeneration workflow
1. Bump pinned Swagger URL/snapshot in `scripts/generate_models.py`.
2. Run `uv run python scripts/generate_models.py`.
3. Run `pytest -m contract` — fails if façade no longer matches generated schema.
4. Update façade as needed; commit both files.

---

## 8. API Client Layer

### Endpoint catalog (all paths under `{base}/api/external/v2`)

| # | Method | Path | Request DTO | Response DTO | Path params | Query params | Errors |
|---|---|---|---|---|---|---|---|
| 1 | POST | `/core/auth/create-access-token-by-service-account` | `CreateAccessTokenByServiceAccountRequestDTO` | `CreateAccessTokenByServiceAccountResponseDTO` | – | – | (auth-specific) |
| 2 | GET | `/core/auth/current-user-data` | – | `CurrentUserDataResponseDTO` | – | – | 401 |
| 3 | POST | `/admin/data/users` | `ListSystemUsersRequestDTO` | `ListSystemUsersResponseDTO` | – | – | 403 |
| 4 | GET | `/core/user-profile/info` | – | `UserProfileInfoDTO` | – | – | 401 |
| 5 | GET | `/admin/manage/users/{userId}/edit` | – | `GetUserForEditResponseDTO` | `userId:int64` | – | 403, 404 |
| 6 | GET | `/communication/posts/data/post-detail-by-id/{postId}` | – | `GetPostDetailResponseDTO` | `postId:int64` | `loadMainAttachment`, `loadMainAttachmentViewLink`, `loadMainAttachmentDownloadLink`, `loadMainAttachmentPreviewImageLink`, `loadMainAttachmentPreviewImageAnimatedLink`, `loadMainAttachmentPreviewImageHiResLink`, `loadMainAttachmentPreviewImageHiResAnimatedLink` (all bool) | 403, 404 |
| 7 | POST | `/communication/posts/data/list/community/{communityId}` | `ListCommunityPostsFilteredRequestDTO` | `PagedListPostsResponseDTO` | `communityId:int64` | `loadPostDetails` (default true), `loadMainAttachment*` (7 flags), `loadCapabilities` | 403, 404 |
| 8 | POST | `/communication/posts/data/comments-list/{postId}` | `ListPostCommentsRequestDTO` | `ListPostCommentsResponseDTO` | `postId:int64` | – | 403, 404 |

### `ListSystemUsersRequestDTO` (key fields)
Pagination: `pageToken`, `pageSize`, `calculateTotalItemsCount`.
Text filters: `fullTextFilter`, `firstNamePrefixFullTextFilter`, `lastNamePrefixFullTextFilter`, `emailPrefixFullTextFilter`, `externalAuthServiceEmailFullTextFilter`, `externalIdFullTextFilter`, `personalEmailFullTextFilter`.
Scope filters: `adminCapabilities`, `statusFilter`, `workspaceIds`, `communityIds`, `businessUnitIds`, `areaIds`, `place`, `role`, `managerIds`, `lang`, `timeZoneIds`, `loginProviderFilter`.
Timestamps: `creationTimestampFrom/To`, `lastAccessTimestampFrom/To`.
Profile flags: `peopleSectionEnabled`, `visibleInPeopleSection`, `reducedProfile`, `viewUserProfiles`.
Sorting: `orderTypeId`, `orderDesc`.

> Fields of `CreateAccessTokenByServiceAccountRequestDTO`, `ListCommunityPostsFilteredRequestDTO`, `ListPostCommentsRequestDTO` could not be enumerated from the Swagger summary fetched at planning time — see **Open question Q5**.

### Resource client design

```python
class ResourceClient:
    def __init__(self, transport: HttpTransport): ...

class AuthAPI(ResourceClient):
    def create_access_token(self, req: CreateAccessTokenByServiceAccountRequestDTO) -> CreateAccessTokenByServiceAccountResponseDTO: ...
    def current_user_data(self) -> CurrentUserDataResponseDTO: ...

class UsersAPI(ResourceClient):
    def list(self, req: ListSystemUsersRequestDTO | None = None, *, page_token: str | None = None,
             page_size: int | None = None, **filters) -> ListSystemUsersResponseDTO: ...
    def iterate(self, req: ListSystemUsersRequestDTO | None = None, **filters) -> Iterator[SystemUser]: ...
    def me(self) -> CurrentUserDataResponseDTO: ...                 # alias for AuthAPI.current_user_data
    def profile(self) -> UserProfileInfoDTO: ...
    def get_for_edit(self, user_id: int) -> GetUserForEditResponseDTO: ...

class PostsAPI(ResourceClient):
    def get(self, post_id: int, *, load_main_attachment: bool = False,
            load_main_attachment_view_link: bool = False, ...) -> GetPostDetailResponseDTO: ...
    def list_in_community(self, community_id: int, req: ListCommunityPostsFilteredRequestDTO | None = None, *,
                          load_post_details: bool = True, **load_flags) -> PagedListPostsResponseDTO: ...
    def iterate_in_community(self, community_id: int, ...) -> Iterator[Post]: ...
    def comments(self, post_id: int, req: ListPostCommentsRequestDTO | None = None) -> ListPostCommentsResponseDTO: ...
    def iterate_comments(self, post_id: int, ...) -> Iterator[PostComment]: ...
```

### Façade
```python
class InteractaClient:
    def __init__(self, base_url: str, *, base_path: str = "/portal", api_version: int = 2,
                 credentials: ServiceAccountKey | None = None, config: Config | None = None,
                 http_client: httpx.Client | None = None): ...
    auth: AuthAPI
    users: UsersAPI
    posts: PostsAPI
    web_urls: WebUrls
    def close(self) -> None: ...
    def __enter__(self) -> "InteractaClient": ...
    def __exit__(self, *exc) -> None: ...
```

---

## 9. Web URL Helper

### Library
```python
client.web_urls.post(post_id=21269)
# -> "https://interacta.example.it/portal/post/21269"
client.web_urls.user(user_id=5225)
# -> "https://interacta.example.it/portal/admin/user/5225/"
client.web_urls.community(community_id=79)
# -> "https://interacta.example.it/portal/community/79"
```

### CLI
A `--web-url` flag added to the read commands that surface a single resource:
- `pynteracta posts get <id> --web-url` → output gains a `web_url` column/field.
- `pynteracta users get <id> --web-url`
- `pynteracta posts list` (per-row `web_url` when flag present).

When `--output json|yaml`, the field is added as `web_url`. When `--output table`, an extra column is appended.

---

## 10. Error Hierarchy

```
InteractaError                       # base
├── AuthenticationError              # 401, token build failure
├── PermissionError                  # 403   (note: distinct from builtin via fully-qualified import)
├── NotFoundError                    # 404
├── ValidationError                  # 400; carries the ValidationErrorResponseDTO payload
│   └── CustomFieldValidationError   # 400 with CustomFieldValidationErrorResponseDTO
├── ConcurrencyError                 # 409 (placeholder; used by future occToken flows)
├── ServerError                      # 5xx
└── TransportError                   # network failures, timeouts, DNS, TLS
```

### Mapping rules (in `transport.py`)
| Status / cause | Exception | Notes |
|---|---|---|
| `httpx.TimeoutException` | `TransportError` | wraps original |
| `httpx.NetworkError` | `TransportError` | |
| 400 with `validationErrors` | `ValidationError` | `.errors: list[FieldError]` |
| 400 with `customFieldValidationErrors` | `CustomFieldValidationError` | |
| 400 other | `ValidationError` | `.errors = []` |
| 401 | `AuthenticationError` | triggers token invalidation |
| 403 | `PermissionError` | |
| 404 | `NotFoundError` | |
| 409 | `ConcurrencyError` | |
| 5xx | `ServerError` | |
| other 4xx | `InteractaError` | |

Every exception carries `status_code`, `request_method`, `request_url` (with token redacted), `response_body` (parsed if JSON), and `request_id` if returned by the API.

No automatic retry in v0.1.

---

## 11. Pagination

### Raw API
Returns the response DTO as-is. Caller inspects `nextPageToken` / `totalItemsCount`.

```python
resp = client.users.list(page_size=50)
while resp.next_page_token:
    resp = client.users.list(page_token=resp.next_page_token, page_size=50)
```

### Iterator API
```python
class PageIterator(Generic[T]):
    def __init__(self, fetch_page: Callable[[str | None], PageLike[T]]): ...
    def __iter__(self) -> Iterator[T]: ...

for user in client.users.iterate(full_text_filter="rossi", page_size=100):
    ...
```
- Lazy: fetches the next page only when the current one is exhausted.
- Stops on empty `nextPageToken`.
- Propagates exceptions raised by the underlying page call.

Applies to: users list (3), posts list-in-community (7), post comments (8).

---

## 12. Observability / Logging

### Setup
- `structlog` configured with: `add_log_level`, `TimeStamper(fmt="iso", utc=True)`, `EventRenamer`, `JSONRenderer` (when not TTY) or `ConsoleRenderer` (when TTY).
- Log level taken from config / `--log-level`.

### Event taxonomy
- `http.request` (method, url, request_id, content_length).
- `http.response` (status, duration_ms, content_length).
- `http.error` (status, error_type, message).
- `auth.token_obtained` (expires_at).
- `auth.token_refreshed`.
- `auth.token_cache_loaded`.

### Redaction processor
- `Authorization` header → `***REDACTED***`.
- SA private key → `***REDACTED***`.
- JWT-looking strings (`eyJ...`) → `***REDACTED***`.
- Body fields whose key matches `(?i)token|password|secret|privateKey` → `***REDACTED***`.

### Hooks
```python
class ClientHooks(Protocol):
    def on_request(self, req: httpx.Request) -> None: ...
    def on_response(self, resp: httpx.Response) -> None: ...
    def on_error(self, exc: BaseException) -> None: ...
```
Registered via `InteractaClient(hooks=...)`.

### User-Agent
`pynteracta/<__version__> python/<python_version> httpx/<httpx_version>`.

---

## 13. CLI Design

### Command tree
```
pynteracta [--profile NAME] [--config-file PATH] [--base-url URL] [--base-path P]
           [--api-version N] [--service-account-key PATH] [--output FMT]
           [--log-level LEVEL] [--no-color] [--quiet]

  auth
    login   --service-account-key PATH  [--profile NAME]
    whoami
    logout                              # purge token cache for current profile

  config
    set <key> <value>     [--profile NAME]
    get <key>             [--profile NAME]
    list                  [--profile NAME]
    use-profile <name>
    add-profile <name>    --base-url URL [...]
    remove-profile <name>

  users
    list    [--full-text TEXT] [--page-size N] [--all] [--web-url]
    get <user_id>                                    [--web-url]
    me
    profile

  posts
    get <post_id>                       [--web-url]
                                        [--load-main-attachment / --no-...]
    list  --community <id>              [--full-text TEXT] [--page-size N] [--all] [--web-url]
    comments <post_id>                  [--page-size N] [--all]
```

### Output formats
- `--output table|json|yaml` (default: `table`). Implemented in `cli/_common.py`.
- Tables rendered with `rich.table.Table`.
- JSON uses pydantic `model_dump_json(indent=2)`.
- YAML uses `ruamel.yaml` (optional dep) — **Open question Q6: include YAML by default or as `pip install pynteracta[yaml]`?**

### Exit codes
| Code | Meaning |
|---|---|
| 0 | success |
| 1 | generic CLI error (bad args, IO) |
| 2 | configuration error |
| 3 | authentication error |
| 4 | permission denied |
| 5 | not found |
| 6 | validation error |
| 7 | transport error |
| 8 | server error |
| 10 | unexpected internal error |

Error rendering: human-friendly message + `request_id` when present + suggestion. `--log-level DEBUG` also prints traceback.

---

## 14. Testing Strategy

### Layout
```
tests/
├── unit/            # respx-based, no network, fast
├── contract/        # generated models ↔ pinned swagger.json
├── integration/     # opt-in, hits a real tenant read-only
└── fixtures/
    └── swagger.json # pinned snapshot
```

### Unit tests (`pytest`)
- One module per source module. Examples:
  - `test_urls.py`: every normalization vector from §5.
  - `test_config.py`: precedence resolution (defaults < file < env < flag).
  - `test_auth.py`: token refresh near expiry; file cache mode 0o600; corrupt cache recovery.
  - `test_transport.py`: error mapping table from §10; redaction.
  - `test_pagination.py`: stop on empty `nextPageToken`; propagate errors.
  - `test_api_users.py` / `test_api_posts.py`: each endpoint mocked with `respx`, asserting URL, headers, body, parsing.

### Contract tests (`@pytest.mark.contract`)
- Load `tests/fixtures/swagger.json`.
- For each in-scope DTO, assert generated pydantic model fields are a superset of swagger schema properties.
- Validate sample response payloads (committed JSON examples) against façade models.
- Fail loudly if a required field disappears or a type changes.

### Integration tests (`@pytest.mark.integration`)
- Skipped by default; enabled via `pytest -m integration`.
- Credentials in `tests/integration/.secrets/sa.json` (git-ignored); `tests/integration/.env.example` documents:
  ```
  PYNTERACTA_BASE_URL=
  PYNTERACTA_BASE_PATH=/portal
  PYNTERACTA_API_VERSION=2
  PYNTERACTA_SERVICE_ACCOUNT_KEY=tests/integration/.secrets/sa.json
  PYNTERACTA_TEST_COMMUNITY_ID=
  PYNTERACTA_TEST_USER_ID=
  PYNTERACTA_TEST_POST_ID=
  ```
- Read-only: `auth.whoami`, `users.profile`, `users.list page_size=1`, `users.get_for_edit`, `posts.get`, `posts.list_in_community page_size=1`, `posts.comments`.
- No mutations under any circumstance.

### Snapshot tests (`syrupy`)
- CLI commands invoked via `typer.testing.CliRunner` against `respx`-mocked transport.
- Snapshots stored per output format.

### Coverage
- Target: **≥ 88%** on `src/pynteracta/` excluding `models/generated/` and `cli/`.
- CLI target: ≥ 70%.
- Enforced in CI via `pytest --cov --cov-fail-under=85`.

---

## 15. Documentation

### MkDocs Material site
```
docs/
├── index.md              # what is pynteracta, disclaimer
├── quickstart.md         # 5-minute library + CLI walkthrough
├── configuration.md      # profiles, precedence, env vars
├── authentication.md     # SA key, token cache
├── urls.md               # API + web URL construction
├── cli.md                # full command reference
├── examples/
│   ├── list-users.md
│   ├── fetch-post.md
│   └── paginated.md
└── api/                  # auto-rendered by mkdocstrings
    ├── client.md
    ├── auth.md
    ├── users.md
    └── posts.md
```
- README: install, quickstart (library + CLI), trademark disclaimer (mandatory).
- All public modules/functions/classes use **Google-style docstrings**.

---

## 16. Quality and Tooling

### Pre-commit (`.pre-commit-config.yaml`)
- `ruff` (check + format) — replaces black/isort/flake8.
- `mypy --strict` (scoped to `src/`).
- `commitizen` or `conventional-pre-commit` to enforce Conventional Commits.
- `check-toml`, `check-yaml`, `end-of-file-fixer`, `trailing-whitespace`.

### Ruff
- `ruff.toml`: `target-version = "py312"`, line length 100, rule set: `E,F,W,I,B,UP,SIM,RUF,N,PT,PL`.
- `models/generated/` excluded.

### Mypy
- `strict = true`, `disallow_any_generics = true`, `warn_return_any = true`.
- Per-module override: `models.generated.*` is `ignore_errors = true`.

### Conventional Commits
- Types used by semantic-release: `feat`, `fix`, `perf`, `refactor`, `docs`, `test`, `build`, `ci`, `chore`, `revert`. `BREAKING CHANGE:` footer triggers major.

---

## 17. GitLab CI/CD

### `.gitlab-ci.yml` (skeleton)
```yaml
# tags: [pynteracta-runner]   # TODO: set self-hosted runner tag
# image: ${CI_REGISTRY}/python:3.12-slim   # TODO: set registry

stages: [lint, type, test, build]

variables:
  UV_CACHE_DIR: .uv-cache

.default-rules:
  rules:
    - if: $CI_COMMIT_BRANCH
    - if: $CI_MERGE_REQUEST_IID

lint:
  stage: lint
  script:
    - pip install uv && uv sync --frozen
    - uv run ruff check .
    - uv run ruff format --check .

type-check:
  stage: type
  script:
    - uv sync --frozen
    - uv run mypy src

test-unit:
  stage: test
  parallel:
    matrix:
      - PY: ["3.12", "3.13"]
  script:
    - uv sync --frozen --python ${PY}
    - uv run pytest -m "not integration and not contract" --cov --cov-report=xml --cov-fail-under=85
  artifacts:
    reports: { coverage_report: { coverage_format: cobertura, path: coverage.xml } }

test-contract:
  stage: test
  script:
    - uv sync --frozen
    - uv run pytest -m contract

build:
  stage: build
  script:
    - uv build
  artifacts:
    paths: [dist/*.whl, dist/*.tar.gz]
    expire_in: 1 year
```

No `publish` job in v0.x — wheels are downloaded from the pipeline artifacts.

---

## 18. Versioning, Changelog, Distribution

### Versioning (`python-semantic-release`)
- Source of truth: git tags + Conventional Commits.
- Pre-1.0 policy: every breaking change still bumps the **minor** (semver pre-1.0 convention) until v1.0 is cut.
- `__version__` injected into `src/pynteracta/__init__.py` at release.

### Changelog (`git-cliff`)
- `cliff.toml` configured to group: Features, Fixes, Performance, Refactors, Documentation, Build, CI, Chores.
- Auto-regenerated on release.

### Distribution policy
| Stream | Mechanism |
|---|---|
| v0.x | GitLab CI build artifact (`.whl`, `.tar.gz`); install via `uv pip install <artifact url>` or downloaded wheel. |
| v1.0+ | Public PyPI (`twine upload` via CI), once the API surface is stable and contract tests have been green for ≥1 month against production. |

---

## 19. Implementation Roadmap

> Each milestone closes with green CI (lint + type + unit + contract) and updated docs.

### M0 — Project scaffolding
- **Deliverables**: `pyproject.toml`, `uv.lock`, `.gitignore`, license, `pre-commit-config`, `ruff.toml`, empty `src/pynteracta/__init__.py`, GitLab CI skeleton (lint+type jobs only).
- **Acceptance**: `uv sync` works; `pre-commit run --all` green; CI lint+type green.
- **Depends on**: —.

### M1 — Configuration, URL building, Auth scaffolding (no real API call yet)
- **Deliverables**: `config.py`, `urls.py`, `exceptions.py`, `logging.py`, skeleton `auth.py` (data classes + cache interface, no JWT yet).
- **Acceptance**: unit tests for URL normalization vectors, config precedence, error class identity all green; mypy strict clean.
- **Depends on**: M0.

### M2 — Transport + error mapping + structured logging
- **Deliverables**: `transport.py` with `httpx.Client` wrapper, redaction processor, error mapping for every row of §10, User-Agent.
- **Acceptance**: respx-based unit tests for each error mapping row; redaction tests prove `Authorization` never appears in log output.
- **Depends on**: M1.

### M3 — Model generation pipeline
- **Deliverables**: `scripts/generate_models.py`; committed `models/generated/external_v2.py`; pinned `tests/fixtures/swagger.json`; first contract tests.
- **Acceptance**: regeneration is reproducible (idempotent diff); contract tests green.
- **Depends on**: M2.

### M4 — Service-account JWT + token cache (real auth call)
- **Deliverables**: complete `auth.py` (JWT assertion build, `TokenManager`, `FileTokenCache`, `MemoryTokenCache`).
- **Acceptance**: unit tests cover refresh-near-expiry, 0o600 enforcement, cache invalidation on 401; one integration test (manual) successfully authenticates against the cert tenant.
- **Depends on**: M3 and resolution of **Q1–Q4**.

### M5 — Resource clients (auth, users, posts) + pagination + web URLs
- **Deliverables**: `api/auth.py`, `api/users.py`, `api/posts.py`, `pagination.py`, `urls.WebUrls`, façade models.
- **Acceptance**: respx unit tests for every endpoint in §8; pagination iterator tests; web URL tests including trailing-slash invariants.
- **Depends on**: M4.

### M6 — CLI
- **Deliverables**: `cli/*` with `auth`, `config`, `users`, `posts` groups; `--output` formats; `--web-url` flag; exit-code map.
- **Acceptance**: `typer` snapshot tests (syrupy) for each command in each output format; CLI integration smoke against mocked transport.
- **Depends on**: M5.

### M7 — Test hardening + documentation + first release
- **Deliverables**: coverage ≥ 88%, integration test suite documented (`.env.example`, secrets layout), MkDocs site, README with disclaimer, `git-cliff` first changelog, `v0.1.0` tag via semantic-release.
- **Acceptance**: docs build green; semantic-release dry-run shows `v0.1.0`; CI artifact contains usable wheel.
- **Depends on**: M6.

### Post-v0.1 roadmap (informational)
- v0.2: write operations on posts/comments (out-of-scope today).
- v0.3: async client.
- v0.4: Google OAuth2.
- v0.5: automatic retry/backoff with jitter.
- v1.0: PyPI publication.

---

## 20. Assumptions and Open Questions

The following items could not be resolved from the Swagger snapshot available at plan-writing time. They must be confirmed before / during the milestone in which they first matter — they are NOT to be guessed.

- **Q1 — Service account key file schema.** The exact JSON layout (field names, encoding of the private key, presence of `kid`/`tokenAudience`) is not documented in the Swagger. Needed by M4. **Action**: obtain a sample SA key from a tenant administrator and pin its schema.
- **Q2 — JWT assertion algorithm.** Expected to be RS256, but not stated in the Swagger. Needed by M4.
- **Q3 — Token expiry signaling.** Whether `CreateAccessTokenByServiceAccountResponseDTO` returns `expiresIn` (seconds), `expiresAt` (epoch/ISO) or only the JWT (with `exp` claim to be decoded) is unknown. Needed by M4.
- **Q4 — `Authorization` header format.** Swagger declares `portal_api_jwt_token` as apiKey in the `Authorization` header. We must confirm whether the raw token or a `Bearer <token>` prefix is expected. Needed by M4.
- **Q5 — Fields of `CreateAccessTokenByServiceAccountRequestDTO`, `ListCommunityPostsFilteredRequestDTO`, `ListPostCommentsRequestDTO`.** The Swagger fetch at planning time did not expose schemas for these. Will be resolved automatically when the Swagger is downloaded in M3 and models are generated; the façade design in §8 must be revisited at that point.
- **Q6 — YAML output dependency.** Make `ruamel.yaml` (or `pyyaml`) a hard dep or an extra (`pynteracta[yaml]`)? Recommendation: extra, to keep the install lean.
- **Q7 — Documented validation error DTOs.** Whether 400 responses use `ValidationErrorResponseDTO`, `CustomFieldValidationErrorResponseDTO`, both, or other shapes was not enumerated in the planning-phase Swagger extract. Needed by M2 for precise mapping.
- **Q8 — Token cache cross-process safety.** A file lock (`filelock`) may be needed when multiple processes share the same profile. Recommendation: add `filelock` in M4 if integration tests reveal contention.
- **Q9 — Server-Side request IDs.** Whether the API returns an `X-Request-Id` (or similar) header is not documented. If present, surface it on every exception (§10).
- **Q10 — Pre-1.0 semver vs strict semver.** Confirm whether breaking changes during v0.x bump minor (lenient, as planned) or major (strict semver).
- **Q11 — Self-hosted GitLab runner tags & registry image.** Placeholders left in `.gitlab-ci.yml`; the actual values must be filled by the platform owner.
- **Q12 — Public tenant for contract test fixtures.** Whether the cert tenant (`cert.development.lab.interacta.space`) is the canonical source for the pinned Swagger snapshot, or whether production Swagger should be tracked separately.
