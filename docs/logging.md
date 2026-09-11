# Audit Logging

`pynteracta` can log every outgoing API call — including request/response headers and (optionally) bodies — to the console and/or a rotating JSON-lines file.

Audit logging is **off by default**.  All audit output is redacted; raw output requires an explicit opt-in with a loud warning.

---

## What is captured

| Always (when audit is on) | Opt-in (`audit_log_bodies`) |
|---|---|
| HTTP method | Request body (JSON payload) |
| Redacted URL | Response body (parsed JSON / truncated text) |
| Redacted request headers | — |
| Response headers | — |
| Status code, duration, `X-Request-Id` | — |

Response bodies larger than 64 KB are truncated with a `...[truncated]` marker.

---

## Enabling via config file

```toml
[profiles.default]
base_url = "https://your-tenant.interacta.cloud"
audit_log = true
audit_log_file = "/var/log/pynteracta/audit.log"
audit_log_bodies = true          # opt-in bodies
audit_log_max_bytes = 10000000   # 10 MB per file
audit_log_backups = 5            # keep 5 rotated files
```

## Enabling via environment variables

| Variable | Default | Description |
|---|---|---|
| `PYNTERACTA_AUDIT_LOG` | `false` | Enable audit logging |
| `PYNTERACTA_AUDIT_LOG_FILE` | _(none)_ | Path to rotating log file; setting this implies `AUDIT_LOG=true` |
| `PYNTERACTA_AUDIT_LOG_BODIES` | `false` | Capture request/response bodies |
| `PYNTERACTA_AUDIT_LOG_RAW` | `false` | Bypass redaction (**unsafe**, see below) |
| `PYNTERACTA_AUDIT_LOG_MAX_BYTES` | `10000000` | Max bytes per log file before rotation |
| `PYNTERACTA_AUDIT_LOG_BACKUPS` | `5` | Number of rotated backup files to keep |

## Enabling via CLI flags

```bash
pynteracta --audit-log \
           --audit-log-file /tmp/audit.log \
           --audit-bodies \
           users list
```

Setting `--audit-log-file` implies `--audit-log` automatically.

---

## Log format

Each entry is a single JSON object on its own line (JSON-lines / NDJSON), written via Python's `RotatingFileHandler`.  Example:

```json
{"event": "audit.request", "log_level": "debug", "logger": "pynteracta.audit", "timestamp": "2026-06-02T10:00:00Z", "method": "GET", "url": "https://tenant.interacta.cloud/.../core/auth/current-user-data", "headers": {"User-Agent": "pynteracta/0.9.1 ...", "Authorization": "***REDACTED***"}, "body": null}
{"event": "audit.response", "log_level": "debug", "logger": "pynteracta.audit", "timestamp": "2026-06-02T10:00:00Z", "status": 200, "url": "...", "headers": {...}, "duration_ms": 134.2, "request_id": "abc-123", "body": {"userId": 42, ...}}
```

---

## Redaction guarantees

- The `Authorization` header is **always** replaced with `***REDACTED***`.
- Any value matching a JWT pattern (`eyJ…`) is replaced — in headers, bodies, and string fields.
- Body keys matching `token`, `password`, `secret`, or `privatekey` (case-insensitive) at **any nesting depth** are replaced.
- Redaction runs on **both** the console and the file handler independently; neither channel ever receives a raw token.

## `--audit-raw`: unsafe redaction bypass

```bash
pynteracta --audit-log --audit-raw users list
```

When `--audit-raw` is set, redaction is **disabled on the audit channel** (the `pynteracta.audit` logger).  A one-time `WARNING` is emitted:

```
audit.redaction_disabled: --audit-raw is active — raw tokens and sensitive data MAY appear in audit output. Never use this in production.
```

> **Never use `--audit-raw` in production.**  It will expose bearer tokens and service-account keys in plain text.

---

## Using the audit logger from library code

When you call `setup_default_logging(audit=True, ...)`, the dedicated `pynteracta.audit` logger is wired up independently of the main `pynteracta` logger.  Audit events (`audit.request`, `audit.response`) are emitted at `DEBUG` level and do not propagate to the root `pynteracta` logger (no double-printing).

```python
from pathlib import Path

from pynteracta.logging import setup_default_logging

setup_default_logging(
    level="INFO",
    audit=True,
    audit_file=Path("/tmp/audit.log"),
    audit_bodies=True,
)
```
