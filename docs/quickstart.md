# Quickstart

## Installation

```bash
uv pip install pynteracta
uv pip install "pynteracta[export]"   # + yaml/parquet export support
```

!!! warning "Upgrading from 0.4.x"
    `pynteracta` 0.9.4 is a from-scratch rewrite published under the same PyPI name. Its API is
    **not compatible** with the 0.4.x line, and the console script was renamed `pynta` →
    `pynteracta`. The old releases are still installable via an explicit pin
    (`pynteracta==0.4.30`).

Wheels and sdists are also attached to each
[GitHub release](https://github.com/simodalla/pynteracta/releases); to pin an exact tag from the
repository, use
`uv pip install "pynteracta @ git+https://github.com/simodalla/pynteracta@v0.9.3"`.

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
