# pynteracta

> *pynteracta is an unofficial third-party Python client for the Interacta™ platform by
> Dinova S.r.l. / Maggioli S.p.A. It is neither sponsored nor endorsed by the vendor.*

An unofficial Python 3.12+ library and CLI client for the Interacta™ REST API (`external_v2`).

## Installation

pynteracta v0.x is distributed as a wheel via GitLab CI artifacts (PyPI publication planned for
v1.0). Download the latest `dist/*.whl` from the pipeline artifacts, then:

```bash
uv pip install pynteracta-0.1.0-py3-none-any.whl
# or with the YAML output extra:
uv pip install "pynteracta-0.1.0-py3-none-any.whl[yaml]"
```

## Quickstart — library

```python
from pynteracta.client import InteractaClient
from pynteracta.auth import load_service_account_key

key = load_service_account_key("sa.json")

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    me = client.users.me()
    print(me.raw.account.full_name)

    for user in client.users.iterate(page_size=100):
        print(user.full_name)
```

## Quickstart — CLI

```bash
# Store your service-account key and authenticate
pynteracta auth login --service-account-key sa.json --base-url https://interacta.example.it

# Who am I?
pynteracta auth whoami

# List users (table output by default)
pynteracta users list --all

# Fetch a post as JSON
pynteracta posts get 21269 --output json

# List posts in a community
pynteracta posts list --community 79 --all --web-url
```

## Features (v0.1)

- Service-account authentication with RS256 JWT, token lifecycle management, and file/memory
  token cache.
- Read-only access: auth/identity, users (list, profile, me, get-for-edit), posts (get,
  list-in-community, comments).
- Lazy pagination iterator — `client.users.iterate()`, `client.posts.iterate_in_community()`.
- 4-level configuration: built-in defaults → config file → env vars → CLI flags.
- Structured logging with token redaction (never logs SA key or access tokens).
- Optional API call audit logging: headers and bodies to console + rotating JSON-lines file, with full redaction and an opt-in raw override for debugging.
- Typer-based CLI with `table`, `json`, and `yaml` output formats.

## Configuration

Config file: `~/.config/pynteracta/config.toml` (Linux/macOS).

```toml
current_profile = "default"

[profiles.default]
base_url = "https://interacta.example.it"
service_account_key = "~/.config/pynteracta/sa.json"
```

Environment variables: `PYNTERACTA_BASE_URL`, `PYNTERACTA_SERVICE_ACCOUNT_KEY`, etc.
See [docs/configuration.md](docs/configuration.md) for the full reference.

## Documentation

Full documentation: `uv run mkdocs serve` (or see the `docs/` directory).

## License

Apache-2.0 — see [LICENSE](LICENSE).
