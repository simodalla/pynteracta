# Example: Paginated Iteration

All `iterate*` methods fetch pages lazily — the next page is only requested when the current
one is exhausted.

```python
from pathlib import Path

from pynteracta.auth import load_service_account_key
from pynteracta.client import InteractaClient

key = load_service_account_key(Path("sa.json"))

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    # Iterate all users
    for user in client.users.iterate(page_size=100):
        print(user.firstName, user.lastName)

    # Iterate posts in a community
    for post in client.posts.iterate_in_community(79, page_size=50):
        print(post.title, client.web_urls.post(post.id))

    # Iterate comments on a post
    for comment in client.posts.iterate_comments(21269, page_size=50):
        print(comment.creationTimestamp, comment.commentPlainText)
```

## Manual pagination

For fine-grained control, use the `list` / `list_in_community` / `comments` methods directly:

```python
resp = client.users.list(page_size=50)
while resp.next_page_token:
    resp = client.users.list(page_token=resp.next_page_token, page_size=50)
    for user in resp.items_typed:
        print(user.firstName, user.lastName)
```
