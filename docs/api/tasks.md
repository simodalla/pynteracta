# Tasks API

The `TasksAPI` client exposes the task-detail read endpoint added in v0.4.0 and, since 0.10.0,
the three write endpoints: create, edit and delete (the first write group opened by ADR 0001).

## Resource grouping

The endpoint is grouped under `client.tasks` (D-v0.4-1), even though a task belongs to a post.
This mirrors the M16 decision to give attachments their own resource group rather than folding
into `PostsAPI`.

## Usage

```python
from pynteracta.client import InteractaClient

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    task = client.tasks.get(7001)
    print(task.id, task.title, task.state)
    print(task.description_plain_text)

    # Sub-tasks and reminders (typed via …1 siblings)
    for st in task.sub_tasks:
        print(st.id, st.description, st.state)
    for r in task.reminders:
        print(r.id, r.value, r.range)

    # Capabilities
    if task.capabilities and task.capabilities.can_modify:
        print("task is editable")

    # Rich-text delta and survey data — reachable only via .raw (D-v0.4-4)
    print(task.raw.descriptionDelta)
    print(task.raw.surveyData)

    # Optimistic-concurrency token, needed by edit()
    print(task.occ_token)
```

## Writing tasks

`create()`, `edit()` and `delete()` mirror the read API: explicit snake_case keyword arguments
for every field of the request DTO, a `*_raw()` variant for callers holding a pre-built DTO, and a
facade over the server response. **Only the fields you pass are sent**; the request body is built
in camelCase from the non-`None` arguments.

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from pynteracta.client import InteractaClient
from pynteracta.exceptions import ConcurrencyError

with InteractaClient(base_url="https://tenant.example.com", credentials=...) as client:
    created = client.tasks.create(
        21269,
        title="Prepare the quarterly report",
        priority=2,
        assignee_user_id=1042,
        watcher_user_ids=[1042, 1099],
        expiration=datetime(2026, 12, 31, 18, 0, tzinfo=ZoneInfo("Europe/Rome")),
        client_uid="report-2026-q4",
    )
    print(created.task_id, created.next_occ_token, created.task.title)

    # Edit: read first, pass the concurrency token explicitly
    task = client.tasks.get(created.task_id)
    try:
        edited = client.tasks.edit(task.id, task.occ_token, title="Prepare the Q4 report")
    except ConcurrencyError:
        # the task changed after we read it: re-read and decide — the library never retries
        raise
    print(edited.next_occ_token)

    post_id = client.tasks.delete(created.task_id)
```

### `TaskWriteResult`

`create()` and `edit()` return a `TaskWriteResult`: `task_id`, `next_occ_token` (the token to
pass to the next `edit()`), `task` (the task data after the write, typed `TaskDetailDTO1`),
`capabilities`, and `.raw` (the generated `CreateTaskResponseDTO` / `EditTaskResponseDTO`).
`delete()` returns the id of the post that contained the task.

### Concurrency: `occ_token`

`edit()` takes the `occ_token` read with `get()` (`Task.occ_token`). If the task changed in the
meantime the server answers `409`, mapped to `ConcurrencyError`. The library does **not** re-read
and retry: that decision belongs to the caller (ADR 0001, non-negotiable rule "no automatic
retries towards Interacta"). The same holds for timeouts and network errors on writes: one request
per call, the outcome stays unknown until you check.

### Expiration

`expiration` must be a timezone-aware `datetime`; a naive one raises `ValueError` before any
request. With an IANA zone (`ZoneInfo`) the local time and the zone name are sent
(`{"datetime": "2026-12-31T18:00:00", "timezone": "Europe/Rome"}`); with a fixed offset the value
is converted to UTC and sent with `"timezone": "UTC"`.

### Omitted fields in `edit()`

Fields you do not pass are not sent. Whether the server keeps or clears them is not documented in
the Swagger: to be confirmed against a test tenant (spec 02, task T11); until then, pass every
field you care about.

## `state` vs `currentWorkflowState`

`Task.state` is an integer lifecycle code (open/closed etc.) — the recommended field to display
and filter on. `Task.current_workflow_state` is the post's workflow-state DTO
(`PostWorkflowDefinitionStateDTO`) and represents the post-level workflow, not the task lifecycle.
Both are exposed on the facade; the CLI default table shows `state` (Q-v0.4-3).

## Description and survey data

Per D-v0.4-4, the facade surfaces `description_plain_text` (curated scalar). The Quill
rich-text JSON (`descriptionDelta`) and survey payloads (`surveyData`,
`surveyDataCommentsInfo`) are left on `.raw` — `surveyData` is an untyped `object → object` map
with no DTO, making `.raw` the only faithful surface.

## API Reference

::: pynteracta.api.tasks.TasksAPI
    options:
      show_source: false
      members:
        - get
        - create
        - create_raw
        - edit
        - edit_raw
        - delete

## Facade Reference

::: pynteracta.models.facade.tasks.Task

::: pynteracta.models.facade.tasks.TaskWriteResult

::: pynteracta.models.facade.tasks.TaskCapabilities

::: pynteracta.models.facade.tasks.SubTask

::: pynteracta.models.facade.tasks.TaskReminder
