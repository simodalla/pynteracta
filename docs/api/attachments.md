# Attachments API

The `AttachmentsAPI` client exposes three read endpoints added in v0.3.0.

## Resource grouping

All three endpoints are grouped under `client.attachments` regardless of their URL prefix.
In particular, `get()` calls `communication/posts/data/attachment-detail-by-id/{id}` — a
`posts/data/` URL — but logically belongs to the attachments resource group (D-v0.3-1).

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    # List all attachments for a post (first page)
    page = client.attachments.list_for_post(21269)
    for att in page.items_typed:
        print(att.id, att.name, att.content_mime_type)

    # Iterate all pages lazily
    for att in client.attachments.iterate_for_post(21269, page_size=20):
        print(att.id, att.name)

    # Fetch a single attachment with parent-post info
    detail = client.attachments.get(3001)
    print(detail.name, detail.post.id if detail.post else None)

    # Check which attachment IDs are visible
    visibility = client.attachments.check_visibility([3001, 3002, 3099])
    print(visibility.ids)  # only visible IDs
```

## Temporary content links

`PostAttachment` and `AttachmentDetail` expose `temporaryContent*Link` properties
(`temporary_content_view_link`, `temporary_content_download_link`, etc.).  These are
short-lived signed URLs returned by the API; they are not shown in the default CLI table
(D-v0.3-3a) but are accessible via `--full`, `--fields`, or `--export` in the CLI and
directly on the facade object in Python.

## Filter surface for `list_for_post`

Curated explicit kwargs: `types`, `entity_types`, `mime_types`, `mime_type_category`,
`order_by`, `order_desc`.

Valid `order_by` values: `'name'`, `'mimeType'`, `'size'`, `'creatorUserId'`,
`'creationTimestamp'`, `'entityType'`.

Niche filters (`aiSupportedFilter`, `postFilePickerFieldId`, `wfScreenFilePickerFieldId`,
`language`) are reachable only via the `list_for_post_raw(req)` escape hatch.

## API Reference

::: pynteracta.api.attachments.AttachmentsAPI
    options:
      show_source: false
      members:
        - list_for_post
        - list_for_post_raw
        - iterate_for_post
        - get
        - check_visibility
        - check_visibility_raw

## Facade Reference

::: pynteracta.models.facade.attachments.PostAttachment

::: pynteracta.models.facade.attachments.PostAttachmentList

::: pynteracta.models.facade.attachments.AttachmentDetail

::: pynteracta.models.facade.attachments.AttachmentVisibility
