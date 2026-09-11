# pynteracta

> *pynteracta is an unofficial third-party Python client for the Interacta™ platform by
> Dinova S.r.l. / Maggioli S.p.A. It is neither sponsored nor endorsed by the vendor.*

`pynteracta` is a Python 3.12+ library and CLI providing a Pythonic, type-safe interface to the
Interacta REST API (`external_v2`). It is synchronous and read-only; the current version is listed
in the [changelog](https://gitlab.unionerenolavinosamoggia.bo.it/ucrls/pynteracta/-/blob/main/CHANGELOG.md).

## What's included (v0.9.x)

- **Authentication** — service-account RS512 JWT assertion with token lifecycle and file/memory
  cache (POSIX `0o600`/`0o700` enforcement), and Google OAuth2 access-token exchange.
- **Read-only resources** — `auth`, `users`, `posts`, `communities`, `catalogs`, `attachments`,
  `tasks`, `groups`, `hashtags`, `admin_manage` (manage/edit forms). Each response is wrapped in a
  hand-written facade with a `.raw` escape hatch to the generated DTO.
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

- Mutations (create/edit/delete on posts, users, comments) — deferred until the read surface has
  been stable for a while.
- Async client, alternate auth methods (Microsoft OAuth2, username/password), automatic
  retry/backoff — tracked under *Deferred / future* in the roadmap, no target version.
- PyPI publication and strict-semver 1.0.

## Quick links

- [Quickstart](quickstart.md) — up and running in 5 minutes.
- [CLI Reference](cli.md) — all commands, flags and exit codes.
- Guides — [Filtering and sorting posts](guides/filtering-posts.md),
  [Filtering and sorting users](guides/filtering-users.md).
- [Authentication](authentication.md), [Configuration](configuration.md),
  [Audit Logging](logging.md), [URL Construction](urls.md).
- [API Reference](api/client.md) — auto-rendered module docs, one page per resource.
- [Testing](testing.md) and [Development Workflow](development-workflow.md).
