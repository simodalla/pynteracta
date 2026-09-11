# pynteracta

> *pynteracta is an unofficial third-party Python client for the Interacta™ platform by
> Dinova S.r.l. / Maggioli S.p.A. It is neither sponsored nor endorsed by the vendor.*

An unofficial Python 3.12+ library and CLI client for the Interacta™ REST API (`external_v2`).
Synchronous, read-only, typed: service-account and Google OAuth2 authentication, ten read
resources, a Typer CLI with table/JSON/YAML output and file export. Current version: see
[`CHANGELOG.md`](CHANGELOG.md).

## Installation

pynteracta v0.x is distributed as a wheel via GitLab CI artifacts (PyPI publication planned for
v1.0). Download `dist/pynteracta-<version>-py3-none-any.whl` from the latest pipeline, then:

```bash
uv pip install pynteracta-<version>-py3-none-any.whl
# with YAML output support:
uv pip install "pynteracta-<version>-py3-none-any.whl[yaml]"
# with Parquet export support:
uv pip install "pynteracta-<version>-py3-none-any.whl[parquet]"
# with all export formats (yaml + parquet):
uv pip install "pynteracta-<version>-py3-none-any.whl[export]"
```

## Quickstart — library

```python
from pathlib import Path

from pynteracta.auth import load_service_account_key
from pynteracta.client import InteractaClient

key = load_service_account_key(Path("sa.json"))

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    # Who am I?
    me = client.users.me()
    ud = me.user_data_typed
    if ud is not None:
        print(ud.firstName, ud.lastName)

    # Lazy pagination over every user
    for user in client.users.iterate(page_size=100):
        print(user.id, user.firstName, user.lastName, user.contactEmail)

    # Filtered, sorted posts of a community
    page = client.posts.list_in_community(
        79, order_by="postCreationTimestamp", order_desc=True, post_types=[1], page_size=50
    )
    for post in page.items_typed:
        print(post.id, post.title, client.web_urls.post(post.id))
```

## Quickstart — CLI

```bash
# Authenticate with a service-account key (global options go BEFORE the command)
pynteracta --base-url https://interacta.example.it auth login --service-account-key sa.json

# Who am I?
pynteracta auth whoami

# List users (table output by default); count matching users only
pynteracta users list --all
pynteracta users list --status 1 --count

# Fetch a post as JSON; list a community's posts with filters and validation
pynteracta posts get 21269 --output json
pynteracta posts list --community 79 --mentioned --field-filter 1411:4:226 --validate --web-url

# Export to file (csv / json / yaml / parquet inferred from the extension)
pynteracta posts list --community 79 --all --export posts.parquet

pynteracta --version
```

## Features (v0.9.x)

- **Authentication** — service-account RS512 JWT assertion with token lifecycle and file/memory
  cache (POSIX `0o600`/`0o700` enforcement), or Google OAuth2 access-token exchange.
- **Read resources** — `auth`, `users`, `posts`, `communities`, `catalogs`, `attachments`,
  `tasks`, `groups`, `hashtags`, `admin_manage` (manage/edit forms). One facade per response with
  a `.raw` escape hatch to the generated DTO.
- **Filtering & sorting** — curated kwargs/flags for posts and users, custom-field and workflow
  screen-field filters with opt-in validation against the community post-definition, generic
  `--filter KEY=VALUE` passthrough.
- **Pagination** — lazy `iterate*()` helpers in Python; `--all`, `--page-token`, `--count` in the
  CLI.
- **CLI output** — `table` / `json` / `yaml`, `--full` and `--fields` field selection,
  `--web-url` deep links, `--export` to csv/json/yaml/parquet.
- **Configuration** — 4-level precedence: built-in defaults → `config.toml` profiles → `PYNTERACTA_*`
  env vars → CLI flags; `config` sub-commands edit the file without losing comments.
- **Logging** — structured logging with token redaction; optional API call audit log to console
  and rotating JSON-lines file.

## Configuration

Config file: `~/.config/pynteracta/config.toml` (Linux/macOS, XDG; `%LOCALAPPDATA%\pynteracta\`
on Windows).

```toml
current_profile = "default"

[profiles.default]
base_url = "https://interacta.example.it"
service_account_key = "~/.config/pynteracta/sa.json"
```

Environment variables: `PYNTERACTA_BASE_URL`, `PYNTERACTA_SERVICE_ACCOUNT_KEY`,
`PYNTERACTA_LOG_LEVEL`, etc. See [docs/configuration.md](docs/configuration.md) for the full
reference.

## Documentation

- [CLI reference](docs/cli.md) — every command, flag and exit code.
- Guides: [filtering and sorting posts](docs/guides/filtering-posts.md),
  [filtering and sorting users](docs/guides/filtering-users.md).
- [Authentication](docs/authentication.md), [configuration](docs/configuration.md),
  [audit logging](docs/logging.md), [testing](docs/testing.md).
- Planning: [`ROADMAP.md`](ROADMAP.md) (what ships when), [`specs/`](specs/) (one spec per
  version), [`WORKFLOW.md`](WORKFLOW.md) (how we work), [`CHANGELOG.md`](CHANGELOG.md).

Full site: `uv run mkdocs serve`.

## License

Apache-2.0 — see [LICENSE](LICENSE).
