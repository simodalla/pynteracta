# Posts

`client.posts` reads posts (detail, lists, comments, history, visibility) and writes **custom
posts** (type 1), comments and workflow data. Event posts (type 2) are read-only for now.

## Writing posts

Every write mirrors the read API: explicit snake_case keyword arguments for every field of the
request DTO, a `*_raw()` variant for callers holding a pre-built DTO, and a facade over the server
response. **Only the fields you pass are sent**, in camelCase. Each call sends **one** request: a
timeout, a network error or a `409` is raised to the caller and never retried by the library.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from pynteracta.client import InteractaClient
from pynteracta.exceptions import ConcurrencyError, ValidationError

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    try:
        created = client.posts.create(
            79,
            title="Safety procedures Q4",
            description="New procedures in force from 1 January.",
            description_format=2,  # 2 = plain text, 1 = Quill delta
            custom_data={"1411": 226, "1413": True},
            watcher_user_ids=[1042],
            client_uid="safety-2026-q4",
            scheduled_publication=datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome")),
        )
    except ValidationError as exc:
        print(exc.response_body)  # e.g. which custom field the server rejected
        raise
    print(created.post_id, created.next_occ_token, created.post.title)

    # Edit replaces the post: read it first, then send back every field that must survive.
    # References (catalog entries, users) are read as objects but written as ids.
    form = client.posts.get_for_edit(created.post_id)
    try:
        edited = client.posts.edit(
            created.post_id,
            form.occ_token,
            title="Safety procedures Q4 (rev. 2)",
            description=form.content_data.descriptionDelta,
            description_format=1,
            custom_data={"1411": 226, "1413": True, "2003": [89]},
            visibility=form.content_data.visibility,
        )
    except ConcurrencyError:
        # the post changed after we read it: re-read and decide — the library never retries
        raise

    client.posts.edit_watchers(created.post_id, add_user_ids=[1099])
    comment = client.posts.add_comment(created.post_id, comment="Read and approved", comment_format=2)

    copy_form = client.posts.get_for_copy(created.post_id)
    copied = client.posts.copy(created.post_id, copy_form.occ_token, title="Safety procedures Q1")

    client.posts.delete(copied.post_id)
```

| Method | Endpoint | Returns |
|---|---|---|
| `get_for_create(community_id)` | `GET …/post-data-for-create/{communityId}` | `PostForCreate` |
| `get_for_edit(post_id, load_attachments=None)` | `GET …/post-data-for-edit/{postId}` | `PostForEdit` (with `occ_token`) |
| `get_for_copy(post_id, load_attachments=None)` | `GET …/post-data-for-copy/{postId}` | `PostForCopy` (with `occ_token`) |
| `create(community_id, …)` / `create_raw` | `POST …/create-post/{communityId}` | `PostWriteResult` |
| `edit(post_id, occ_token, …)` / `edit_raw` | `PUT …/edit-post/{postId}/{occToken}` | `PostWriteResult` |
| `edit_custom_data(post_id, occ_token, …)` / `edit_custom_data_raw` | `PUT …/edit-post-custom-data/{postId}/{occToken}` | `PostWriteResult` |
| `copy(post_id, occ_token, …)` / `copy_raw` | `PUT …/copy-post/{postId}/{occToken}` | `PostWriteResult` (the **new** post) |
| `edit_watchers(post_id, add_user_ids, remove_user_ids)` / `edit_watchers_raw` | `PUT …/edit-post-watchers/{postId}` | `None` |
| `edit_attachments(post_id, add, update, remove_ids)` / `edit_attachments_raw` | `PUT …/edit-post-attachments/{postId}` | `PostAttachmentsWriteResult` |
| `delete(post_id)` | `DELETE …/delete-post/{postId}` | the `postId` |
| `mark_as_erasable(post_id)` | `PUT …/mark-post-as-erasable/{postId}` | the server's `postId` (observed: `0`) |
| `add_comment(post_id, …)` / `add_comment_raw` | `POST …/create-comment/{postId}` | `PostComment` |
| `get_workflow_screen(post_id, operation_id=None)` | `GET …/post-workflow-screen-data-for-edit/{postId}` | `WorkflowScreen` (with `screen_occ_token`) |
| `execute_workflow_operation(post_id, operation_id, …)` / `_raw` | `POST …/execute-post-workflow-operation/{postId}/{opId}` | `WorkflowOperationResult` |
| `edit_workflow_screen(post_id, screen_occ_token, …)` / `_raw` | `PUT …/edit-post-workflow-screen-data/{postId}/{token}` | `WorkflowScreenWriteResult` |

All paths are under `communication/posts/manage/`.

### Concurrency: `occ_token`

The post detail (`get()`) carries no concurrency token. `edit()`, `edit_custom_data()` and
`copy()` take the `occ_token` read with `get_for_edit()` or `get_for_copy()`; the workflow screen
has its own `screen_occ_token`, read with `get_workflow_screen()`. Every successful write returns
the token for the next one (`next_occ_token`, `next_screen_occ_token`). If the post changed in the
meantime the server answers `409`, raised as `ConcurrencyError`: the library does **not** re-read
and retry (ADR 0001). `edit_watchers()`, `edit_attachments()`, `delete()`, `mark_as_erasable()`
and `add_comment()` need no token.

### Custom fields and descriptions

`custom_data` is a dict keyed by custom-field id (`{"1411": 226}`), sent as is: the server
validates it against the community's post definition, and a rejected value raises
`ValidationError` with the server's detail in `exc.response_body`. `description` is sent in the
format given by `description_format`: `1` = Quill delta (the server's default, and the format
`get_for_edit()` returns in `content_data.descriptionDelta`), `2` = plain text. Comments work the
same way with `comment` and `comment_format`.

### Scheduled publication

`scheduled_publication` must be a timezone-aware `datetime`; a naive one raises `ValueError`
before any request. With an IANA zone the local time and the zone name are sent
(`{"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"}`); with a fixed offset the value
is converted to UTC.

### Attachments

`attachments`, `add_attachments`, `update_attachments` and `edit_attachments()` accept files
just uploaded with `client.attachments.upload()` (an `UploadedAttachment`, sent as `name` +
`contentRef`) and attachments the server already knows (`attachmentId`, or `name` +
`contentRef`), as dicts or `InputPostAttachmentDTO1` models. For a new version of an attachment
pass `uploaded.as_version_of(attachment_id)` in `update_attachments` (or `update`). See
[Uploading files](attachments.md#uploading-files).

### `edit()` and `copy()` are replacements

Fields you do not pass are not sent, and the server treats `edit()` as a **replacement**, not a
patch: a missing description counts as empty, so an `edit()` with only a title fails with `400
REQUIRED_FIELD` on `description` (verified against a tenant). Read the post with
`get_for_edit()` (or `get_for_copy()` before a copy) and send back every field that must survive,
as in the example above. `copy()` behaves the same way: the copy does not inherit the fields you
omit, so send back the description, custom data and visibility read with `get_for_copy()`.
`description_format=2` (plain text) is accepted by `edit()` too. The CLI commands `posts edit`,
`posts edit-custom-data` and `posts copy` do all this for you.

### References are written as ids

Custom fields and workflow screen fields that point to catalog entries, users or groups are
**read** as full objects (`"2003": [{"id": 89, "catalogId": 12, "label": "3 - Bassa", …}]`) but
must be **written** as ids (`"2003": [89]`): sending the objects back fails with `400
INVALID_VALUE`. Rich-text (delta) fields are written as Quill delta unless the request sets
`delta_area_format=2`, which applies to every delta field of the request.

### Workflow

`client.posts.capabilities(post_id).workflow_permitted_operations` lists the transitions the
caller may execute (`id`, `name`, `fromState`, `toState`). A transition with a screen needs its
data and token:

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    caps = client.posts.capabilities(21269)
    operation = caps.workflow_permitted_operations[0]
    screen = client.posts.get_workflow_screen(21269, operation_id=operation.id)
    # screen.screen_data returns references as objects: write them back as ids
    result = client.posts.execute_workflow_operation(
        21269,
        operation.id,
        screen_data={"5233": [8341], "5237": [3872]},
        screen_occ_token=screen.screen_occ_token,
    )
    print(result.new_current_state.name, [op.name for op in result.new_permitted_operations])
```

A transition without a screen is executed with no arguments: the server accepts the empty body
(verified against a tenant). `edit_workflow_screen()` changes the screen data of the current state,
with the token read by `get_workflow_screen(post_id)`; all the transitions of a post share that
`screen_occ_token`. When the screen data of the current state are not editable
(`capabilities().can_edit_workflow_screen_data` is `False`), `get_workflow_screen(post_id)`
without `operation_id` raises `PermissionError` (`403`); the screen of a permitted transition can
still be read with `operation_id`.

### Delete and mark as erasable

`delete()` and `mark_as_erasable()` both make the post unreadable through the API (`404` on
every read afterwards). `mark_as_erasable()` also marks it for future physical erasure; its
response carries `postId: 0` on the tenants observed so far, and the method returns that value
as is. The CLI reports the id you asked for.

## API Reference

::: pynteracta.api.posts
    options:
      members:
        - PostsAPI

::: pynteracta.api.posts_write.PostsWriteAPI
    options:
      show_source: false

## Facade Reference

::: pynteracta.models.facade.posts_write
    options:
      show_source: false
      members:
        - PostWriteResult
        - PostForCreate
        - PostForEdit
        - PostForCopy
        - PostComment
        - PostAttachmentsWriteResult
        - WorkflowScreen
        - WorkflowOperationResult
        - WorkflowScreenWriteResult
