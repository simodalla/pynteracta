# Hashtags API

The `HashtagsAPI` client exposes the community hashtag listing endpoint added in v0.5.0.

## Resource grouping

The endpoint is grouped under `client.hashtags` (D-v0.5-1), separate from community or post
resource clients.

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    # List hashtags for a community
    page = client.hashtags.list_for_community(79)
    for ht in page.items_typed:
        print(ht.id, ht.name, ht.external_id)

    # Iterate all pages lazily
    for ht in client.hashtags.iterate_for_community(79, name="eng"):
        print(ht.id, ht.name)

    # Include deleted hashtags
    page = client.hashtags.list_for_community(79, include_deleted=True)
```

## Sort fields

Valid `order_by` values: `'name'`, `'externalId'`. `order_desc` controls direction
(default: descending).

## API Reference

::: pynteracta.api.hashtags.HashtagsAPI
    options:
      show_source: false
      members:
        - list_for_community
        - list_for_community_raw
        - iterate_for_community

## Facade Reference

::: pynteracta.models.facade.hashtags.Hashtag

::: pynteracta.models.facade.hashtags.HashtagList
