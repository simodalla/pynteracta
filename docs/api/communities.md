# communities API

::: pynteracta.api.communities.CommunitiesAPI
    options:
      show_source: false
      members:
        - list
        - list_by_view_post_capability
        - details
        - details_bulk
        - details_bulk_raw
        - post_definition
        - post_definitions
        - post_definitions_raw

---

## Communities by post-view capability

`list()` returns the communities the caller can **post** in. `list_by_view_post_capability()`
returns those where the caller can **view** posts at a given capability level, in the same
`CommunityList` shape.

```python
from pynteracta.client import InteractaClient
from pynteracta.models.facade.communities import ViewPostCapabilityLevel

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    everything = client.communities.list_by_view_post_capability()
    public = client.communities.list_by_view_post_capability(ViewPostCapabilityLevel.PUBLIC)
    private = client.communities.list_by_view_post_capability("private")  # case-insensitive
    print([c.name for c in public.items_typed])
```

- `level` is a `ViewPostCapabilityLevel` (`PRIVATE`, `PUBLIC`, `ALL`) or its name as a string,
  in any case. Any other value raises `ValueError` **before** the request.
- Without a level the query parameter is not sent and the answer is the server's choice. On the
  test tenant, with a service account, it matched `ALL`; every level returned the same 15
  communities, while `list()` returned 9.
- A `403` raises `PermissionError`; a timeout raises `TransportError`. One request, never
  retried.

## Facade models

::: pynteracta.models.facade.communities.CommunityList

::: pynteracta.models.facade.communities.Community

::: pynteracta.models.facade.communities.CommunityDetail

::: pynteracta.models.facade.communities.PostDefinition

::: pynteracta.models.facade.communities.PostFieldDefinition

::: pynteracta.models.facade.communities.PostDefinitionMap

::: pynteracta.models.facade.communities.FieldType

::: pynteracta.models.facade.communities.ViewPostCapabilityLevel
