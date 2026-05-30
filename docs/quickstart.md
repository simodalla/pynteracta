# Quickstart

## Installation

pynteracta v0.x wheels are distributed via GitLab CI artifacts.

```bash
uv pip install pynteracta-0.1.0-py3-none-any.whl
```

## CLI quickstart

```bash
# Authenticate with a service-account key
pynteracta auth login \
  --service-account-key sa.json \
  --base-url https://interacta.example.it

# Verify authentication
pynteracta auth whoami

# List users
pynteracta users list --all

# Fetch a post
pynteracta posts get 21269 --output json
```

## Library quickstart

```python
from pynteracta.client import InteractaClient
from pynteracta.auth import load_service_account_key

key = load_service_account_key("sa.json")

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    # Who am I?
    me = client.users.me()
    print(me.raw.account.full_name)

    # Iterate all users lazily
    for user in client.users.iterate(page_size=100):
        print(user.full_name, user.email)

    # Get a post
    post = client.posts.get(21269)
    print(post.title, client.web_urls.post(21269))
```

## Next steps

- [Configuration](configuration.md) — profiles, env vars, precedence.
- [Authentication](authentication.md) — SA key fields, token cache, POSIX security.
- [CLI Reference](cli.md) — all commands.
- [Examples](examples/list-users.md) — complete worked examples.
