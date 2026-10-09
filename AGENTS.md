# AGENTS.md

This file provides agent-specific guidance for pynteracta. For general project setup, architecture, testing, and code conventions, see [CLAUDE.md](CLAUDE.md).

## Claude Code Skills

The following Claude Code skills are available for automated tasks:

### `sddpa:*` (plugin `sddpa`, marketplace `ucrls`)
The spec-driven cycle that replaces the former `new-version` skill: `/sddpa:specifica <ambito>` →
`/sddpa:piano <nn>` → `/sddpa:task <nn>` → `/sddpa:implementa [<nn>] <task>` → `/sddpa:verifica <nn>`,
plus `/sddpa:adr <titolo>`. `specifica` creates the branch and writes `specs/<nn>-<nome>/spec.md`;
`verifica` closes the spec, logs the `M<n>` section in `PROGRESS.md` and proposes the merge. See
[CLAUDE.md > Metodo](CLAUDE.md#metodo) and [WORKFLOW.md](WORKFLOW.md).

### `release`
Cuts a pynteracta release — the RELEASE phase from WORKFLOW.md, on `main` after the version's specs
are closed by `/sddpa:verifica` and merged. Flips the ROADMAP row to ✅ Shipped (one-file `docs:`
commit; the spec is already frozen by `verifica`), then drives version bump + tag via
python-semantic-release and regenerates CHANGELOG with git-cliff. A version may bundle several specs.

### `verify`
Verifies that a code change works by running the app and observing behavior. Use when asked to run/start the app, take screenshots, or confirm a fix works in the real app (not just tests).

### `code-review`
Reviews the current diff for correctness bugs and reuse/simplification/efficiency cleanups. Pass `--comment` to post inline PR findings, or `--fix` to apply them to the working tree.

### `simplify`
Reviews changed code for reuse, simplification, efficiency, and altitude cleanups, then applies fixes. Quality only — does not hunt for bugs; use `code-review` for that.

## General Reference

- **Branch discipline**: Always follow the STOP rule — create a feature/bugfix/milestone branch before any change. See [CLAUDE.md > STOP — Workflow obbligatorio](CLAUDE.md#stop--workflow-obbligatorio-prima-di-ogni-modifica).
- **Commands**: See [CLAUDE.md > Commands](CLAUDE.md#commands).
- **Architecture**: See [CLAUDE.md > Architecture](CLAUDE.md#architecture).
- **Testing**: See [CLAUDE.md > Testing Layout](CLAUDE.md#testing-layout).
- **Code conventions**: See [CLAUDE.md > Code Conventions](CLAUDE.md#code-conventions).
- **Planning documents**: See [CLAUDE.md > Planning Documents](CLAUDE.md#planning-documents).
