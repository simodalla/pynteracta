# pynteracta

[![CI](https://github.com/simodalla/pynteracta/actions/workflows/ci.yml/badge.svg)](https://github.com/simodalla/pynteracta/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://github.com/simodalla/pynteracta/blob/main/LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![Docs](https://img.shields.io/badge/docs-github.io-blue.svg)](https://simodalla.github.io/pynteracta/)

> *pynteracta is an unofficial third-party Python client for the Interacta™ platform by
> Dinova S.r.l. / Maggioli S.p.A. It is neither sponsored nor endorsed by the vendor.*

An unofficial Python 3.12+ library and CLI client for the Interacta™ REST API (`external_v2`).
Synchronous, read-only, typed: service-account and Google OAuth2 authentication, ten read
resources, a Typer CLI with table/JSON/YAML output and file export. Current version: see
[`CHANGELOG.md`](https://github.com/simodalla/pynteracta/blob/main/CHANGELOG.md).

## Installation

```bash
uv pip install pynteracta
# with YAML output support:
uv pip install "pynteracta[yaml]"
# with Parquet export support:
uv pip install "pynteracta[parquet]"
# with all export formats (yaml + parquet):
uv pip install "pynteracta[export]"
```

> **Upgrading from 0.4.x?** The API changed completely — see
> [the compatibility note](#note-for-users-of-pynteracta-04x-and-earlier) at the end of this page.

Each release is also attached as a wheel and sdist to its
[GitHub release](https://github.com/simodalla/pynteracta/releases). To pin an exact tag from the
repository instead:

```bash
uv pip install "pynteracta @ git+https://github.com/simodalla/pynteracta@v0.9.3"
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
`PYNTERACTA_LOG_LEVEL`, etc. See [docs/configuration.md](https://github.com/simodalla/pynteracta/blob/main/docs/configuration.md) for the full
reference.

## Documentation

Full documentation: **<https://simodalla.github.io/pynteracta/>**

- [CLI reference](https://github.com/simodalla/pynteracta/blob/main/docs/cli.md) — every command, flag and exit code.
- Guides: [filtering and sorting posts](https://github.com/simodalla/pynteracta/blob/main/docs/guides/filtering-posts.md),
  [filtering and sorting users](https://github.com/simodalla/pynteracta/blob/main/docs/guides/filtering-users.md).
- [Authentication](https://github.com/simodalla/pynteracta/blob/main/docs/authentication.md), [configuration](https://github.com/simodalla/pynteracta/blob/main/docs/configuration.md),
  [audit logging](https://github.com/simodalla/pynteracta/blob/main/docs/logging.md), [testing](https://github.com/simodalla/pynteracta/blob/main/docs/testing.md).
- Planning: [`ROADMAP.md`](https://github.com/simodalla/pynteracta/blob/main/ROADMAP.md) (what ships when), [`specs/`](https://github.com/simodalla/pynteracta/blob/main/specs/) (one spec per
  version), [`WORKFLOW.md`](https://github.com/simodalla/pynteracta/blob/main/WORKFLOW.md) (how we work), [`CHANGELOG.md`](https://github.com/simodalla/pynteracta/blob/main/CHANGELOG.md).

To preview the site locally: `uv run mkdocs serve`.

## License

Apache-2.0 — see [LICENSE](https://github.com/simodalla/pynteracta/blob/main/LICENSE).

## Note for users of pynteracta 0.4.x and earlier

**Version 0.9.4 and every later version are a complete rewrite of this project.** The package name
on PyPI is the same, but the code is not: the library was rebuilt from scratch, and its public API
is **not compatible** with the `0.4.x` line. (PyPI jumps straight from `0.4.30` to `0.9.4`: the
rewrite's earlier versions were released on GitHub only.) Upgrading from `0.4.x` will break your code, and there
is no migration path — the two versions share no common API surface.

What changed:

| | `0.4.30` and earlier | `0.9.4` and later |
|---|---|---|
| Library API | `pynteracta.api` / `pynteracta.core` / `pynteracta.schemas` | `InteractaClient` + `pynteracta.api.*` resource clients |
| CLI command | `pynta` | **`pynteracta`** |
| HTTP backend | `requests` | `httpx` |
| License | BSD-3-Clause | **Apache-2.0** |
| Scope | read + write | read-only surface (writes deferred) |

**If you depend on the old line**, it is still published and installable — nothing has been removed
or yanked. Pin it explicitly:

```bash
uv pip install "pynteracta==0.4.30"
```

The `0.4.x` releases receive no further updates. New work happens on the rewrite.
