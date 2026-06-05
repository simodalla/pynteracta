# Tasks API

The `TasksAPI` client exposes the single task-detail read endpoint added in v0.4.0.

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

    # occToken is carried on .raw for future write use
    print(task.raw.occToken)
```

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

## Facade Reference

::: pynteracta.models.facade.tasks.Task

::: pynteracta.models.facade.tasks.TaskCapabilities

::: pynteracta.models.facade.tasks.SubTask

::: pynteracta.models.facade.tasks.TaskReminder
