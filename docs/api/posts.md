# Posts

`client.posts` reads posts (detail, lists, comments, history, visibility) and writes **custom
posts** (type 1), comments and workflow data, and **event posts** (type 2): create, edit, copy and
the answer to the invitation (see [Event posts](#event-posts)).

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

## Event posts

Event posts have their own create, edit and copy endpoints, a form read for each, and the answer
to the invitation. The event block is built from flat keyword arguments: dates, time zone,
all-day flag, location and invitees. The same rules as for custom posts apply: only the fields
you pass are sent, one request per call, a `409` raised as `ConcurrencyError` and never retried.
Watchers, attachments, delete, mark-as-erasable and comments of an event post use the methods
above (`edit_watchers()`, `edit_attachments()`, `delete()`, …): the endpoints are the same for
every post type.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from pynteracta.client import InteractaClient
from pynteracta.models.facade import ParticipationAnswer

rome = ZoneInfo("Europe/Rome")

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    created = client.posts.create_event(
        79,
        start_at=datetime(2026, 11, 5, 10, 0, tzinfo=rome),
        end_at=datetime(2026, 11, 5, 12, 0, tzinfo=rome),
        location="Room A",
        invited_user_ids=[1042],
        invited_group_ids=[3],
        invitation_type_id=2,  # 0 = guest, 2 = collaborator, for every invitee
        title="Quarterly review",
        description="Agenda in the attachment.",
        description_format=2,
        client_uid="review-2026-q4",
    )

    form = client.posts.get_event_for_edit(created.post_id)
    event = form.event  # EventData, or None if the server returns no event block
    print(form.occ_token, event.start_at, event.timezone, event.location, event.my_answer)
    print([(u.id, u.name, u.type_id) for u in event.invited_users])

    client.posts.edit_event(created.post_id, form.occ_token, location="Room B")
    client.posts.participate(created.post_id, ParticipationAnswer.YES, notes="Arriving late")

    copy_form = client.posts.get_event_for_copy(created.post_id)
    copied = client.posts.copy_event(
        created.post_id,
        copy_form.occ_token,
        title="Quarterly review (Q1)",
        start_at=datetime(2027, 2, 4, 10, 0, tzinfo=rome),
        end_at=datetime(2027, 2, 4, 12, 0, tzinfo=rome),
    )
```

| Method | Endpoint | Returns |
|---|---|---|
| `get_event_for_create(community_id)` | `GET …/event-post-data-for-create/{communityId}` | `EventPostForCreate` |
| `get_event_for_edit(post_id, load_attachments=None)` | `GET …/event-post-data-for-edit/{postId}` | `EventPostForEdit` (with `occ_token` and `event`) |
| `get_event_for_copy(post_id, load_attachments=None)` | `GET …/event-post-data-for-copy/{postId}` | `EventPostForCopy` (with `occ_token` and `event`) |
| `create_event(community_id, *, start_at, …)` / `create_event_raw` | `POST …/create-event-post/{communityId}` | `PostWriteResult` |
| `edit_event(post_id, occ_token, …)` / `edit_event_raw` | `PUT …/edit-event-post/{postId}/{occToken}` | `PostWriteResult` |
| `copy_event(post_id, occ_token, …)` / `copy_event_raw` | `PUT …/copy-event-post/{postId}/{occToken}` | `PostWriteResult` (the **new** post) |
| `participate(post_id, answer, notes=None)` / `participate_raw` | `PUT …/post-event/{postId}/partecipate` | `None` |

### Dates and time zone

`start_at` (required by `create_event()`) and `end_at` are timezone-aware `datetime` objects; a
naive one raises `ValueError` before any request. The library sends each date as a local
date-time without offset (`"startAt": {"localDatetime": "2026-11-05T10:00:00"}`) plus the IANA
name of the zone of `start_at` in `event.timezone`; `end_at` is converted into that zone. With a
fixed offset (no IANA name) both are converted to UTC and `"UTC"` is sent. In `edit_event()` and
`copy_event()`, where `start_at` is optional, the zone comes from `end_at` when `start_at` is
missing. `all_day=True` sends `allDay: true` and leaves the dates as they are.

`EventData.start_at` and `end_at` are timezone-aware `datetime` objects too: read from
`zonedDatetime` when the server sends it, otherwise from `localDatetime` in the event's
`timezone`, and `None` when neither is available.

### Invitees and answers

`invited_user_ids` and `invited_group_ids` become `event.invitations.users` and `.groups`, as
`{"id": N}` items; with `invitation_type_id` every item also gets `"typeId"` (`0` guest, `2`
collaborator). Different types per invitee need the `*_raw` variant with a prebuilt DTO.
`send_edit_post_notifications=True` notifies the invitees when the post is edited.
`EventData.invited_users` and `invited_groups` list `EventInvitee` objects (`id`, `name`,
`type_id`, `.raw`).

`participate()` records the answer of the authenticated identity: the technical identity with a
service account, the linked user with Google OAuth2. `answer` is a `ParticipationAnswer`
(`YES = 1`, `MAYBE = 2`, `NO = 3`) or its integer value; anything else raises `ValueError`
before the request. `EventData.my_answer` is the answer already given, `None` if there is none.
The server answers `404` (`NotFoundError`) for a post that does not exist or is not an event.

### Cover image, watcher groups and pinning

`cover_image_content_ref` is the `contentRef` of an image uploaded with
`client.attachments.upload()` (see [Uploading files](attachments.md#uploading-files)).
`watcher_group_ids` (create) and `add_watcher_group_ids` / `remove_watcher_group_ids` (edit,
copy) work like their user counterparts. `pinned=None` leaves the pin as it is. `link_preview`
is sent as given, in the shape of `LinkPreviewDTO`.

### Omitted fields in `edit_event()` and `copy_event()`

Only the fields you pass are sent, and inside `event` only the keys you pass. What the server
does with the omitted fields and event keys is **to be confirmed** against a tenant; until then
read the post with `get_event_for_edit()` (or `get_event_for_copy()`) and send back every field
that must survive. The CLI commands `posts edit-event` and `posts copy-event` do this for you.
Write responses carry the post in `postData`; when the server includes the `event` block there,
the CLI shows its dates and location, otherwise those columns stay empty.

## API Reference

::: pynteracta.api.posts
    options:
      members:
        - PostsAPI

::: pynteracta.api.posts_write.PostsWriteAPI
    options:
      show_source: false

::: pynteracta.api.posts_event.PostsEventAPI
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

::: pynteracta.models.facade.posts_event
    options:
      show_source: false
      members:
        - EventData
        - EventInvitee
        - EventPostForCreate
        - EventPostForEdit
        - EventPostForCopy
        - ParticipationAnswer
