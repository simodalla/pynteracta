# pynteracta

> *pynteracta is an unofficial third-party Python client for the Interacta™ platform by
> Dinova S.r.l. / Maggioli S.p.A. It is neither sponsored nor endorsed by the vendor.*

`pynteracta` is a Python 3.12+ library and CLI providing a Pythonic, type-safe interface to the
Interacta REST API (`external_v2`). It is synchronous, with full read access and a write surface
that grows one resource group at a time; the current version and its contents are listed in the
[changelog](https://github.com/simodalla/pynteracta/blob/main/CHANGELOG.md).

## What's included

- **Authentication** — service-account RS512 JWT assertion with token lifecycle and file/memory
  cache (POSIX `0o600`/`0o700` enforcement), and Google OAuth2 access-token exchange.
- **Read resources** — `auth`, `users`, `posts`, `communities`, `catalogs`, `attachments`,
  `tasks`, `groups`, `hashtags`, `admin_manage` (manage/edit forms). Each response is wrapped in a
  hand-written facade with a `.raw` escape hatch to the generated DTO.
- **Write operations** — `tasks` create, edit and delete; custom `posts` create, edit, copy,
  custom data, watchers, attachments, delete and mark-as-erasable, comments and workflow
  transitions and screen data. In the library (explicit kwargs plus `*_raw` variants) and in the
  CLI (`tasks create|edit|delete`, `posts create|edit|copy|comment|delete|workflow-execute|…`, with
  confirmation for destructive commands). Optimistic concurrency is surfaced as
  `ConcurrencyError` / exit code `9`; a write that fails with an unknown outcome is never retried
  automatically. More write groups (event posts, admin) follow.
- **Attachment upload** — `client.attachments.upload()` sends a file to the tenant's storage
  and returns a reference that post, comment and task writes accept; in the CLI `--attach` on
  the write commands, `attachments upload` and `posts edit-attachments`.
- **Filtering & sorting** — curated kwargs and CLI flags for posts and users, custom-field and
  workflow screen-field filters, a label-based filter builder, opt-in validation against the
  community post-definition.
- **Lazy pagination** — `iterate*()` helpers fetch pages on demand; the CLI offers `--all`,
  `--page-token` and `--count`.
- **4-level configuration** — built-in defaults → config file profiles → `PYNTERACTA_*` env vars →
  CLI flags.
- **Structured logging** with token redaction, plus an opt-in API call audit log.
- **Typer CLI** with `table` / `json` / `yaml` output, `--full` / `--fields` selection, `--web-url`
  deep links and `--export` to csv/json/yaml/parquet.

## What's out of scope for now

- Writes on event posts and the admin area — planned, not yet shipped; see the
  [roadmap](https://github.com/simodalla/pynteracta/blob/main/ROADMAP.md).
- Async client, alternate auth methods (Microsoft OAuth2, username/password), automatic
  retry/backoff — tracked under *Deferred / future* in the roadmap, no target version.
- Strict-semver 1.0.

## Quick links

- [Quickstart](quickstart.md) — up and running in 5 minutes.
- [CLI Reference](cli.md) — all commands, flags and exit codes.
- Guides — [Filtering and sorting posts](guides/filtering-posts.md),
  [Filtering and sorting users](guides/filtering-users.md).
- [Authentication](authentication.md), [Configuration](configuration.md),
  [Audit Logging](logging.md), [URL Construction](urls.md).
- [API Reference](api/client.md) — auto-rendered module docs, one page per resource.
- [Testing](testing.md) and [Development Workflow](development-workflow.md).
