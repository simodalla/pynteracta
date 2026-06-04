# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] — 2026-06-04

### Chores

- Scaffold project (M0)
- Add AGENTS.md for Cursor agent guidance

### Documentation

- Apply targeted revisions to development plan

### Features

- Implement M1 — config, URL building, auth scaffolding
- Implement M2 — transport, error mapping, structured logging
- Implement M3 — model generation pipeline
- Implement M4 — service-account JWT auth and token cache
- Implement M5 — resource clients, pagination, and InteractaClient
- Implement M6 — CLI (auth/config/users/posts commands)
- Merge M5+M6 — resource clients, pagination, and CLI
- Add --full and --fields per-command output options to all data-emitting commands
- Add --export / --export-format to all data-emitting CLI commands

### Bug Fixes

- Accept --output both globally and per data-emitting command
- Default token cache dir now follows XDG config location
- Expand ~ (tilde) in config file paths before validation
- Default Authorization scheme to Bearer
- Fix --fields crash on null schema fields; --web-url honoured with --full/--fields
- Patch customData/currentWorkflowScreenData to dict[str, Any] at codegen time


