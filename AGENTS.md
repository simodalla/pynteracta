# AGENTS.md

This file provides agent-specific guidance for pynteracta. For general project setup, architecture, testing, and code conventions, see [CLAUDE.md](CLAUDE.md).

## Claude Code Skills

The following Claude Code skills are available for automated tasks:

### `new-version`
Scaffolds the next pynteracta minor version — implements PLAN + BRANCH phases from [WORKFLOW.md](WORKFLOW.md). Creates the feature branch (per the STOP rule), writes `specs/vX.Y-<slug>.md` with the canonical 7-section shape, and adds the ⏳ row to the ROADMAP version table. See [CLAUDE.md > Planning Documents](CLAUDE.md#planning-documents) for the planning doc strategy.

### `release`
Cuts a pynteracta minor release — implements the RELEASE phase from WORKFLOW.md after the version's work is merged to main. Flips the ROADMAP row to ✅ Shipped, freezes the spec header, then drives version bump + tag via python-semantic-release and regenerates CHANGELOG with git-cliff.

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
