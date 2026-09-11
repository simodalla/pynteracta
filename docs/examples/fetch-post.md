# Example: Fetch a Post

```python
from pathlib import Path

from pynteracta.auth import load_service_account_key
from pynteracta.client import InteractaClient

key = load_service_account_key(Path("sa.json"))

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    post = client.posts.get(21269, load_main_attachment=True)
    print(post.title)
    print(post.creation_timestamp)  # epoch-ms; raw DTO: post.raw.creationTimestamp

    # Deep-link URL to the post in the web app
    print(client.web_urls.post(21269))
```
