# Example: List Users

```python
from pynteracta.client import InteractaClient
from pynteracta.auth import load_service_account_key

key = load_service_account_key("sa.json")

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    # Single page
    resp = client.users.list(page_size=50, full_text_filter="rossi")
    for user in resp.items_typed():
        print(user.full_name, user.email)

    # All pages via iterator
    for user in client.users.iterate(page_size=100):
        print(user.full_name, user.account_id)
```
