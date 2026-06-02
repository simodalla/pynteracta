# pynteracta

> *pynteracta is an unofficial third-party Python client for the Interacta™ platform by
> Dinova S.r.l. / Maggioli S.p.A. It is neither sponsored nor endorsed by the vendor.*

`pynteracta` is a Python 3.12+ library and CLI providing a Pythonic, type-safe interface to the
Interacta REST API (`external_v2`).

## What's included in v0.1

- **Service-account authentication** — RS256 JWT assertion, token lifecycle, file and memory
  token cache with POSIX `0o600`/`0o700` enforcement.
- **Read-only resource access** — auth/identity, users (4 endpoints), posts (3 endpoints).
- **Lazy pagination** — `iterate()` helpers fetch pages on demand.
- **4-level configuration** — built-in defaults → config file → env vars → CLI flags.
- **Structured logging** with automatic token redaction.
- **Typer CLI** with `table`, `json`, and `yaml` output formats.

## What's out of scope for v0.1

- Mutations (create/edit/delete on posts, users, comments).
- Google OAuth2 authentication.
- Async API (planned for v0.3).
- PyPI publication (planned for v1.0).

## Quick links

- [Quickstart](quickstart.md) — up and running in 5 minutes.
- [CLI Reference](cli.md) — all commands and flags.
- [API Reference](api/client.md) — auto-rendered module docs.
- [Testing](testing.md) — unit, contract, and integration test guide.
