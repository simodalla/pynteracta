---
name: new-version
description: Scaffold the next pynteracta minor version — phases PLAN + BRANCH of WORKFLOW.md. Creates the dedicated branch (STOP rule), writes specs/vX.Y-<slug>.md from the canonical 7-section shape pre-filled from the ROADMAP read-surface inventory, and adds the ⏳ row to the ROADMAP version table. Use when starting a new version/minor/milestone ("nuova versione", "scaffold vX.Y", "inizia il prossimo minor", "plan the next version"). Stops before any implementation.
---

# new-version — scaffold the next minor (PLAN + BRANCH)

Automates phases **1. PLAN** and **2. BRANCH** of [`WORKFLOW.md`](../../../WORKFLOW.md) for `pynteracta`.
The output is a branch + a `specs/` file + a ROADMAP row, ready for the user to refine. **It does
not implement anything** — façade/api/cli/tests/docs are the IMPLEMENT phase and are out of scope.

## Critical ordering — branch BEFORE writing files

`WORKFLOW.md` lists PLAN before BRANCH, but the **STOP rule** in [`CLAUDE.md`](../../../CLAUDE.md)
forbids touching any file while on `main`. This skill resolves the tension by **creating the branch
first**, then writing the spec and editing the ROADMAP. Never write the spec while on `main`.

## Procedure

### 1. Determine the scope (version + milestone + slug)

1. Read [`ROADMAP.md`](../../../ROADMAP.md): the **Versions** table and the **Read-surface inventory**.
2. **Next version number**: the lowest minor not yet shipped/in-progress. Pre-1.0 cadence is *one
   read-endpoint group per minor* (`0.X.0 → 0.(X+1).0`).
3. **Next milestone `M<n>`**: last milestone used in the table `+ 1`. Note the legacy gap **M11–M13
   is skipped** — never reuse those numbers. (As of this writing the last used is M19.)
4. **Slug**: short kebab-case theme, e.g. `admin-manage-edits`, `groups-hashtags`. The spec file is
   `specs/vX.Y-<slug>.md`.
5. If the user did **not** name the scope, propose the next inventory group from the ROADMAP and
   confirm before proceeding. If the inventory has no remaining group, surface the **Deferred /
   future** backlog and ask which to plan.

### 2. Create the branch (STOP rule — do this before any file write)

```bash
git checkout -b m<n>_<slug>      # milestone work — preferred for a new version
# or feature_<slug> / bugfix_<slug> per the kind of work
git branch --show-current        # MUST NOT print "main"
```

Abort the whole skill if the branch is still `main`.

### 3. Write `specs/vX.Y-<slug>.md`

Create the file using the **template** below. Pre-fill section 2 (endpoints) from the matching
group in the ROADMAP **Read-surface inventory** — paths, methods, and response DTOs are already
listed there. Keep deliverables/decisions concrete by mirroring the most recent shipped spec
(`specs/v0.5-groups-hashtags.md`, `specs/v0.4-tasks.md`) — same module layout: `models/facade/`,
`api/`, `client.py` registration, `cli/`, re-exports.

Leave genuine unknowns as **Open questions** (Q-vX.Y-n) rather than guessing. The header banner
starts in **PLANNING** state; the `release` step (separate, future skill) flips it to FROZEN.

### 4. Add the ROADMAP version-table row

Insert one row at the bottom of the **Versions** table, marked in progress:

```
| **0.X.0** | <Theme> | M<n> | ⏳ In progress | [specs/vX.Y-<slug>.md](specs/vX.Y-<slug>.md) |
```

Do not touch any other table row, and do not edit PROGRESS.md or CHANGELOG.md (those belong to the
LOG and RELEASE phases).

### 5. Stop and hand back

Report to the user: branch name, spec path, the endpoints pre-filled, and the open questions that
need their input. **Do not start implementing.** Do not commit unless the user asks (per CLAUDE.md).

---

## Spec template (the canonical 7-section shape)

```markdown
# pynteracta vX.Y.0 — <Theme> (M<n>)

> **Status: PLANNING — ⏳ In progress.** Spec for the next minor. Read-only, additive. No change to existing flows.
> Follows the conventions of the [foundation spec](v0.1-foundation.md), the
> [<most-recent> spec](v0.Z-<slug>.md), and the patterns logged in
> [`PROGRESS.md`](../PROGRESS.md) (M5 resource clients, <relevant Mn refs>).
> Index: [`ROADMAP.md`](../ROADMAP.md).

## 1. Objective

<1–2 paragraphs: what surface this minor exposes, why, and that it targets a minor bump
0.X.0 → 0.(X+1).0 via a `feat:` commit with existing clients unchanged.>

## 2. Endpoints in scope

All paths under `{base}/api/external/v2/`.

| # | Method | Path | Request DTO | Response DTO |
|---|---|---|---|---|
| 1 | <GET/POST> | `<path>` | <DTO or –> | `<ResponseDTO>` |

**Codegen stub → typed mapping:**
- <notes on DTO types, nullable fields, occToken, pagination, etc.>

> **Out of scope:** <related endpoints deferred, e.g. write/PUT operations>.

## 3. Deliverables

- **`models/facade/<module>.py`** (new) — facade(s) over the response DTO(s) with curated fields and
  `.raw` escape hatch; re-export from `models/facade/__init__.py` and `models/__init__.py`.
- **`api/<module>.py`** (new) — `<Name>API(ResourceClient)` with explicit-kwargs methods (+ `*_raw`).
- **`client.py`** — register `self.<group> = <Name>API(...)`.
- **`cli/<module>.py`** (new Typer sub-app) wired through `render_output`.
- Unit + contract tests + JSON fixtures; docs (`docs/cli.md`, `docs/api/*.md`).

## 4. Resolved decisions

- **D-vX.Y-1 — <topic>.** <decision>.

## 5. Open questions

- **Q-vX.Y-1 — <topic>.** <to confirm during implementation>.

## 6. Out of scope

- <write operations / unrelated surfaces / deferred items>.
```

## Guardrails

- Never edit a frozen spec — supersede it with a new file.
- Never hand-edit `CHANGELOG.md` (git-cliff) or pre-fill `PROGRESS.md` (LOG phase).
- Regenerate `models/generated/` only if the swagger changed — not part of this skill.
- One read-endpoint group per minor; do not bundle multiple groups into one version.
