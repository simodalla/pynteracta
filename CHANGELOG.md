# Changelog

All notable changes to this project will be documented in this file.
## [0.2.0] - 2026-06-04

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


