---
name: release
description: Cut a pynteracta minor release — phase 6 RELEASE of WORKFLOW.md, after the version's work is merged to main. Flips the ROADMAP row to ✅ Shipped, freezes the spec header, then drives the version bump + tag with python-semantic-release (Option A) and regenerates the CHANGELOG with git-cliff. Use when finishing/shipping a version ("rilascia vX.Y", "chiudi il minor", "release vX.Y.0", "freeze the spec and tag"). Never pushes or publishes without an explicit request.
---

# release — cut the minor (RELEASE phase)

Automates phase **6. RELEASE** of [`WORKFLOW.md`](../../../WORKFLOW.md) for `pynteracta`. This is the
**one operation that commits on `main`** — the STOP rule's branch discipline is for feature work;
the release commits land on `main` after the merge.

## Release model — Option A (semantic-release is the driver)

The package version is **dynamic**: hatchling reads `__version__` from
`src/pynteracta/__init__.py` (`[tool.hatch.version]`). Ownership of the moving parts:

| Concern | Owner | Notes |
|---|---|---|
| Version number + git tag + `__version__` bump | **python-semantic-release** | Computed from Conventional Commits since the last tag. `tag_format = "v{version}"`, `major_on_zero = false`, `allow_zero_version = true`. |
| `CHANGELOG.md` | **git-cliff** | Per CLAUDE.md. semantic-release runs with `--no-changelog` so the two never fight. |
| ROADMAP row + spec freeze | **this skill** (a `chore:` doc commit) | The 2-file commit, like the historical `chore: release` commits. |

> **Invariant:** between releases, `__version__` equals the last released tag. semantic-release
> re-establishes this on every release. If you find it drifted, sync it first with a `chore:` commit —
> do not let a build go out with a stale version.

## Pre-flight checks (abort if any fails — report, don't force)

1. **Merged.** The version's work is already merged to `main` (the `feat:` commit + its merge are in
   `git log main`). This skill does **not** merge feature branches.
2. **On main.** `git branch --show-current` == `main`. The release commits land here.
3. **Clean tree.** `git status --porcelain` is empty (no stray WIP from another branch). If dirty,
   stop — never sweep unrelated changes into the release.
4. **Gate green.** `uv run ruff check . && uv run ruff format --check . && uv run mypy src && uv run pytest --cov --cov-fail-under=85`.
5. **Logged.** `PROGRESS.md` has the `M<n>` section for this version (phase 5 LOG done). If missing,
   stop and run the LOG step first.
6. **Spec is PLANNING.** The spec header still reads `Status: PLANNING — ⏳ In progress`. If already
   frozen, the version was likely released — stop.
7. **Version invariant.** `__version__` in `src/pynteracta/__init__.py` equals the last tag
   (`git describe --tags --abbrev=0`). If not, sync it with a `chore:` commit before releasing.

## Actions

Compute the **next version** first — never guess it. Preview with semantic-release:

```bash
uv run semantic-release version --print        # prints the computed next version, no side effects
```

Use that `vX.Y.0` and **today's date** (YYYY-MM-DD) below.

### 1. Doc commit — flip ROADMAP + freeze spec (the 2-file commit)

- **ROADMAP row.** In the **Versions** table of [`ROADMAP.md`](../../../ROADMAP.md), change only this
  version's Status cell: `⏳ In progress` → `✅ Shipped <today>`. Touch no other row.
- **Spec header.** In `specs/vX.Y-<slug>.md`, rewrite only the Status line:
  `Status: PLANNING — ⏳ In progress.` → `Status: SHIPPED — vX.Y.0 (<today>). Frozen. Do not edit.`
  Keep the rest byte-for-byte. Do not edit any other frozen spec.
- **Commit** on `main`, staging only those two files (explicit paths, never `git add -A`):
  ```
  chore: release vX.Y.0 — flip ROADMAP to shipped, freeze spec header

  Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
  ```

### 2. Version bump + tag (semantic-release)

```bash
uv run semantic-release version --no-changelog --no-push --no-vcs-release --skip-build
```

- `--no-changelog` → git-cliff owns `CHANGELOG.md` (next step), not semantic-release.
- `--no-push --no-vcs-release` → **nothing leaves the machine**; push is a separate, explicit step.
- `--skip-build` → building the wheel is CI's job; keep the release step side-effect-light.

This bumps `__version__`, creates its own version commit, and tags `vX.Y.0`. Verify with
`git show --stat HEAD` and `git tag --points-at HEAD`.

### 3. CHANGELOG (git-cliff)

Regenerate and commit separately — never hand-edit `CHANGELOG.md`:

```bash
uv run git-cliff --tag vX.Y.0 -o CHANGELOG.md
git commit -m "docs: update CHANGELOG for vX.Y.0" CHANGELOG.md
```

(The changelog has sometimes been regenerated in **batches** covering several versions — if that is
the intent, say so and batch instead of committing per release.)

### 4. Hand back

Report the doc commit SHA, the semantic-release version commit + tag, and the changelog commit.
**Do not push and do not create a remote release** unless the user explicitly asks; then:
`git push origin main --follow-tags`. PyPI stays off (`upload_to_pypi = false`).

## Guardrails

- The doc commit = **exactly two files** (ROADMAP + spec header). The version bump is semantic-release's
  own separate commit — never fold them together.
- Never run `semantic-release version` without `--no-push --no-vcs-release` unless the user asked to
  publish — its default behaviour pushes and creates a remote release.
- Never hand-edit `CHANGELOG.md`; never edit a different version's frozen spec.
- Commit on `main` is allowed only for the release commits; all other work is on a branch.
