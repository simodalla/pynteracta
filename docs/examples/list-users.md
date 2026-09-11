# Example: List Users

```python
from pathlib import Path

from pynteracta.auth import load_service_account_key
from pynteracta.client import InteractaClient

key = load_service_account_key(Path("sa.json"))

with InteractaClient(
    base_url="https://interacta.example.it",
    credentials=key,
) as client:
    # Single page — items_typed is a property yielding ListSystemUsersElementDTOModel
    resp = client.users.list(page_size=50, full_text_filter="rossi")
    for user in resp.items_typed:
        print(user.firstName, user.lastName, user.contactEmail)

    # All pages via iterator
    for user in client.users.iterate(page_size=100):
        print(user.id, user.firstName, user.lastName)
```
