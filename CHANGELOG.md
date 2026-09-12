# Changelog

All notable changes to this project will be documented in this file.
## [0.9.2] - 2026-09-12

### CI

- Replace GitLab CI with GitHub Actions

### Chores

- Point repository URLs at GitHub
- Neutralise GITHUB_ACTIONS colour forcing in CLI tests
- **deps**: Upgrade all packages to latest compatible versions
- Release v0.9.2 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Update CHANGELOG for v0.9.1
- Align documentation with the move to GitHub
- Log M24 in PROGRESS.md

### Fixes

- **deps**: Upgrade cryptography and pydantic-settings for security advisories

## [0.9.1] - 2026-09-11

### Chores

- Add static consistency check for docs Python snippets
- Point repository URLs at the internal GitLab
- Release v0.9.1 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Update CHANGELOG for v0.9.0
- **spec**: Add v0.9.1 docs-alignment spec and ROADMAP row (M23)
- Align README and docs with the v0.9 API and CLI surface
- Log M23 in PROGRESS.md

### Fixes

- **cli**: Honour log_level from profile and environment

## [0.9.0] - 2026-09-11

### Chores

- Neutralise FORCE_COLOR/CLICOLOR_FORCE in unit tests
- Release v0.9.0 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Update CHANGELOG for v0.8.0
- Add v0.9.0 minor-enhancements spec and ROADMAP row (M22)
- **spec**: Promote features 2-13 into v0.9.0 deliverables, resolve Q-v0.9-1/2
- Add users filtering guide and expose guides/testing in MkDocs nav (M22 group D)
- Fix Python snippets to match the real API surface
- Log M22 in PROGRESS.md

### Features

- **cli**: Add --screen-field-filter to posts list (M22, v0.9.0 Feature 1)
- **cli**: Surface remaining list kwargs as flags (M22 group A)
- **cli**: Opt-in --validate, typed --filter tokens, EpochMs consistency (M22 group B)
- **cli**: --version, --count and --page-token on posts/users list (M22 group C)

### Fixes

- Accept epoch-ms given as a digit string in date filter kwargs

## [0.8.0] - 2026-06-11

### Chores

- Release v0.8.0 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Update CHANGELOG for v0.7.0
- Refactor AGENTS.md to reference CLAUDE.md, eliminate duplication

### Features

- Add curated filter & sort kwargs to users list (M21, v0.8.0)

### Fixes

- Respect --asc/--desc flag without --order-by in posts list

## [0.7.0] - 2026-06-08

### Chores

- Add /new-version and /release Claude Code skills
- Release v0.7.0 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Update CHANGELOG for v0.6.0
- Align /release skill to Option A (semantic-release-driven)
- Log M20 in PROGRESS.md

### Features

- Post filter & sort completeness (M20, v0.7.0)

### Fixes

- Always send complete communityPostFilters/communityAttachmentFilters baselines
- Render epoch-ms timestamps as datetime strings in table output

## [0.6.0] - 2026-06-08

### Documentation

- Regenerate CHANGELOG.md for v0.3.0–v0.5.0
- Make WORKFLOW.md version-agnostic process guide
- De-date development-workflow page, fix WORKFLOW.md link host
- Drop foundation-spec row from CLAUDE.md planning list
- Resolve Q-v0.6-2 — CLI command tree confirmed
- Freeze v0.6.0 spec + mark M19 shipped in ROADMAP

### Features

- Plan v0.6.0 — Admin manage edits (read forms)
- Admin manage edits read forms (M19, v0.6.0)

## [0.5.0] - 2026-06-05

### Chores

- Release v0.5.0 — flip ROADMAP to shipped, freeze spec header

### Features

- Add groups & hashtags read surface (M18, v0.5.0)

## [0.4.0] - 2026-06-05

### Chores

- Release v0.4.0 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Add v0.4 tasks spec (M17)

### Features

- Add tasks read surface (M17, v0.4.0)

## [0.3.0] - 2026-06-05

### Chores

- Release v0.3.0 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Add v0.3 attachments spec (M16)

### Features

- Add attachments read surface (M16, v0.3.0)
- Release v0.3.0 — attachments read surface (M16)

### Fixes

- Allow null values in workflowScreenData for PostActivityHistoryEventDTO

## [0.2.0] - 2026-06-04

### Chores

- Release v0.2.0

### Documentation

- Restructure planning docs into ROADMAP + per-version specs

### Features

- Add seven posts data/* read endpoints (M15, v0.2.0)
- Merge M15 — posts read completeness (v0.2.0)

## [0.1.0] - 2026-06-04

### Chores

- Scaffold project (M0)
- Add AGENTS.md for Cursor agent guidance
- Release v0.1.0

### Documentation

- Apply targeted revisions to development plan
- Add integration test guide and update index
- Log Authorization-scheme regression bugfix in PROGRESS.md
- Merge PROGRESS.md update for Authorization-scheme bugfix

### Features

- Implement M1 — config, URL building, auth scaffolding
- Implement M2 — transport, error mapping, structured logging
- Implement M3 — model generation pipeline
- Implement M4 — service-account JWT auth and token cache
- Implement M5 — resource clients, pagination, and InteractaClient
- Implement M6 — CLI (auth/config/users/posts commands)
- Merge M5+M6 — resource clients, pagination, and CLI
- Implement M7 — docs, release tooling, and test hardening
- Merge M7 — docs, release tooling, and test hardening
- Implement config add-profile and remove-profile commands
- **auth**: Align JWT assertion with official Interacta docs (RS512, constant aud, Bearer)
- **dx**: Enforce branch discipline via CLAUDE.md + pre-edit hook
- Merge feature_fix_cli_docs — CLI doc fixes + branch discipline enforcement
- **docs**: Merge feature_integration_test_docs — integration test guide
- **auth**: Add Google OAuth2 device-flow authentication
- Merge feature_google_oauth2 — Google OAuth2 device-flow authentication
- Add CommunicationSettings API — communities + catalogs (M9)
- Merge feature_communication_settings — CommunicationSettings API (M9)
- Add audit logging — rotating JSON-lines API call log with redaction
- Merge feature_audit_logging — audit logging with redaction (M10)
- Use XDG config path on Linux and macOS
- Merge feature_xdg_config_path — XDG config path on Linux/macOS
- Merge bugfix_bearer_auth_scheme — default Authorization to Bearer
- Merge bugfix_integration_test_credentials — fix integration test fixtures
- Add --full and --fields per-command output options to all data-emitting commands
- Merge feature_full_fields_output — --full and --fields CLI output options
- Add --export / --export-format to all data-emitting CLI commands
- Merge feature_export_files — --export / --export-format CLI data export

### Fixes

- **docs**: Correct three CLI doc divergences from actual code
- Default Authorization scheme to Bearer in InteractaClient
- Correct integration test fixtures for auth and communities
- Expand ~ (tilde) in config file paths before validation
- Default token cache dir now follows XDG config location
- Merge bugfix_token_cache_xdg_dir — default token cache dir XDG
- Accept --output both globally and per data-emitting command
- Merge bugfix_output_placement — hybrid --output placement
- --fields no longer errors on null schema fields; --web-url honoured with --full/--fields
- Merge bugfix_fields_null_and_weburl — --fields null crash and --web-url+--full/--fields
- Patch customData/currentWorkflowScreenData to dict[str, Any] at codegen time
- Merge bugfix_custom_data_schema_types — dict[str, Any] for polymorph fields

### Style

- Ruff format config.py decorator line


