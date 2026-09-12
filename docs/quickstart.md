# Quickstart

## Installation

pynteracta v0.x wheels are attached to each
[GitHub release](https://github.com/simodalla/pynteracta/releases) (PyPI publication is planned
for v1.0). Install straight from a tag:

```bash
uv pip install "pynteracta @ git+https://github.com/simodalla/pynteracta@v0.9.1"
uv pip install "pynteracta[export] @ git+https://github.com/simodalla/pynteracta@v0.9.1"   # + yaml/parquet export support
```

Alternatively, download the wheel from the release page and `uv pip install` the local file.

## CLI quickstart

```bash
# Authenticate with a service-account key (--base-url is a global option: it goes BEFORE the command)
pynteracta --base-url https://interacta.example.it \
  auth login --service-account-key sa.json

# Verify authentication
pynteracta auth whoami

# List users
pynteracta users list --all

# Fetch a post
pynteracta posts get 21269 --output json
```

## Library quickstart

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

    # Iterate all users lazily
    for user in client.users.iterate(page_size=100):
        print(user.firstName, user.lastName, user.contactEmail)

    # Get a post
    post = client.posts.get(21269)
    print(post.title, client.web_urls.post(21269))
```

## Next steps

- [Configuration](configuration.md) — profiles, env vars, precedence.
- [Authentication](authentication.md) — SA key fields, token cache, POSIX security.
- [CLI Reference](cli.md) — all commands.
- [Examples](examples/list-users.md) — complete worked examples.
