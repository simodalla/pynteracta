# Attachments API

The `AttachmentsAPI` client reads attachments (list, detail, visibility) and uploads new files
that can then be attached to posts, comments and tasks.

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

## Uploading files

Interacta uploads a file in two steps: the API returns a temporary storage URL with a **signed
upload policy**, then the file is sent there as a multipart `POST` form. `upload()` does both and
returns an `UploadedAttachment` (`content_ref`, `name`, `mime_type`, `temporary_download_url`,
`.raw`), which the write methods of posts, comments and tasks accept directly.

```python
from pathlib import Path

from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    report = client.attachments.upload(Path("report.pdf"))           # name and MIME from the file
    data = client.attachments.upload(b"a,b\n1,2\n", name="data.csv")  # bytes need a name
    client.posts.create(79, title="Q4 report", attachments=[report, data])

    # a new version of an existing attachment (id 9466)
    v2 = client.attachments.upload(Path("report-v2.pdf"))
    client.posts.edit_attachments(21269, update=[v2.as_version_of(9466)])
```

- `upload(file, *, name=None, mime_type=None)` accepts a `Path` or a path string (read in
  streaming and closed by the library), `bytes`, or a binary file object you opened (left
  open). With `bytes` or a file object `name` is required. The MIME type is guessed from the
  name's extension (`application/octet-stream` when unknown) unless `mime_type` is given. A
  missing path, a directory or a missing name raise **before** any request.
- `UploadedAttachment` goes wherever a write accepts attachments (`attachments`,
  `add_attachments`, `add`) and is sent as `{"name", "contentRef"}`; `as_version_of(id)` gives
  `{"attachmentId", "contentRef", "name"}` for `update_attachments` / `update`. The server applies
  the new name to the new version (verified against a tenant). Dicts and DTOs already accepted
  keep working, also mixed with uploaded files.
- `request_upload_url()` performs only the first step and returns an `UploadTicket`
  (`content_ref`, `upload_url`, `form_params`, `temporary_download_url`), for callers that upload
  the file with another tool.

**Errors and retries.** Each step sends **one** request and never retries. A storage response
other than 2xx (expired policy, file too large) raises `UploadError` with `status_code`,
`response_body` (the storage's XML, as is), the redacted `request_url` and `file_name`; a timeout
or network error raises `TransportError`, with an unknown outcome. `timeout_seconds` applies to
each network operation of the upload, not to its total duration: raise it for large files.

**Secrets.** The storage request never carries the Interacta token. It goes through hooks and
the audit log with its URL and status only: neither the file content nor the policy fields are
ever logged, even with `audit_log_bodies`. The `policy` and `signature` fields and the
`Signature` of signed URLs are redacted everywhere (see [Audit Logging](../logging.md)).

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
        - upload
        - request_upload_url

## Facade Reference

::: pynteracta.models.facade.attachments.PostAttachment

::: pynteracta.models.facade.attachments.PostAttachmentList

::: pynteracta.models.facade.attachments.AttachmentDetail

::: pynteracta.models.facade.attachments.AttachmentVisibility

::: pynteracta.models.facade.attachments.UploadedAttachment

::: pynteracta.models.facade.attachments.UploadTicket

::: pynteracta.exceptions.UploadError
