# Changelog

All notable changes to this project will be documented in this file.
## [0.12.0] - 2026-10-10

### Chores

- Fixture e contract test della risposta di upload-new-attachment; riga 0.12.0 in ROADMAP (04-T01)
- Caratterizzazione della redazione delle query e dei corpi non validi di posts create (04-T02)
- Integration test opt-in del ciclo upload, allegato, nuova versione, rimozione (04-T14)
- Fixture e contract test dei DTO di scrittura di utenti e gruppi; riga 0.13.0 in ROADMAP (05-T01)
- Redazione di password e generatedPassword in audit log e hook (05-T07)
- Integration test opt-in dei cicli di scrittura di gruppi e utenti (05-T14)

### Documentation

- Aggiornamento del CHANGELOG per v0.11.0
- Spec 04, upload degli allegati
- Piano 04, upload degli allegati
- Task 04, upload degli allegati
- Esito della prova sul tenant dell'upload degli allegati (04-T15)
- Upload degli allegati in libreria e CLI, redazione dei link firmati (04-T16)
- PRD con RF-024 precisato, RF-024a, RNF-001 e RNF-011 (04-T17)
- Verifica 04, upload degli allegati
- Spec 05, anagrafiche admin: utenti e gruppi
- Piano 05, anagrafiche admin: utenti e gruppi
- Task 05, anagrafiche admin: utenti e gruppi
- **spec**: Revisione della spec 05 dopo la prova sul tenant, criteri 05-C27..29 e task T18
- **spec**: Esito di T15, la prova dei cicli di scrittura sul tenant (05-T15)
- Scritture admin di utenti e gruppi in libreria e CLI (05-T16)
- PRD con RF-023 precisato, RF-023a, RF-023b, RF-023c e RF-023d (05-T17)
- Verifica 05, anagrafiche admin prima metà: utenti e gruppi (05)
- Release v0.12.0, riga di ROADMAP a shipped

### Features

- **transport**: POST multipart verso lo storage senza token né corpo nei log, UploadError (04-T05)
- **api**: Façade UploadTicket e UploadedAttachment, protocollo WriteInput nei corpi di scrittura (04-T06)
- **api**: Upload degli allegati in due passi su client.attachments (04-T07)
- **api**: UploadedAttachment accettato dalle scritture di post e task (04-T08)
- **cli**: Exit code 11 per gli upload falliti e helper per --attach (04-T09)
- **cli**: Comando attachments upload (04-T10)
- **cli**: --attach su posts create, comment, edit e copy (04-T11)
- **cli**: --attach su tasks create ed edit (04-T12)
- **cli**: Comando posts edit-attachments con upload, nuove versioni e rimozioni (04-T13)
- **users**: Occ_token sulle façade per-edit e façade UserWriteResult (05-T02)
- **groups**: Façade GroupSummary, GroupWriteResult e GroupMembersResult (05-T03)
- **users**: Creazione, modifica, eliminazione e credenziali degli utenti su client.users (05-T04)
- **groups**: Creazione, modifica ed eliminazione dei gruppi su client.groups (05-T05)
- **groups**: Modifica dei membri di uno o più gruppi, conflitto del 200 come ConcurrencyError (05-T06)
- **cli**: Comando users create con credenziali e password da stdin o generata (05-T09)
- **cli**: Users edit ed edit-credentials come patch con occToken letto o imposto (05-T10)
- **cli**: Users delete con conferma (05-T11)
- **cli**: Comandi groups create, edit (patch) e delete con conferma (05-T12)
- **cli**: Groups edit-members per un gruppo o in blocco da --json (05-T13)

### Fixes

- **logging**: Redazione delle firme negli URL e delle chiavi signature e policy (04-T03)
- **users**: GeneratedPassword stringa dal tenant normalizzata in lista, errore di forma senza valori (05-T15)
- **cli**: Users edit-credentials invia solo i blocchi indicati; GET 204 vuota è NotFoundError (05-T18)

### Refactors

- **transport**: Request scomposta in helper condivisi (04-T04)
- **cli**: Read_password e opzioni --json e --occ-token condivise in cli/_write.py (05-T08)

## [0.11.0] - 2026-10-10

### Chores

- Fixture e contract test dei DTO di scrittura dei post, dati di screen come valori qualsiasi (03-T02)
- Integration test opt-in del ciclo di scrittura dei post (03-T15)
- Campi custom obbligatori e dettaglio dell'errore nell'integration test dei post (03-T15)
- Dettaglio del server per ogni passo che fallisce nell'integration test dei post (03-T15)
- La copia dell'integration test rimanda i campi letti (03-T15)

### Documentation

- Aggiornamento del CHANGELOG per v0.10.0
- Home, README e quickstart aggiornati alla superficie di scrittura, senza numeri di versione
- Spec 03, scrittura dei post custom, commenti e workflow
- Piano 03, scrittura dei post custom, commenti e workflow
- Task 03, scrittura dei post custom, commenti e workflow
- Spec, piano e task 03 rivisti, dati di screen del workflow da rigenerare
- Scrittura dei post nelle pagine API e CLI, home e README, variabili per gli integration test (03-T14)
- Spec, piano e task 03 rivisti, riferimenti letti scritti come id
- Esito delle prove sul tenant per la spec 03 (03-T16)
- PRD e pagine aggiornate con l'esito delle prove sul tenant per la spec 03 (03-T17)
- Verifica 03, scrittura dei post custom, commenti e workflow
- Release v0.11.0, riga di ROADMAP a shipped

### Features

- **api**: PUT senza corpo di risposta vale come oggetto vuoto; riga 0.11.0 in ROADMAP (03-T01)
- **posts**: Façade per le risposte di scrittura, le letture propedeutiche, i commenti e il workflow (03-T03)
- **posts**: Capabilities di copia, allegati e operazioni di workflow permesse (03-T04)
- **posts**: Letture propedeutiche con occ_token e creazione di un post (03-T05)
- **posts**: Modifica, campi custom e copia di un post con occToken (03-T06)
- **posts**: Watcher, allegati, eliminazione, marcatura per la cancellazione e commenti (03-T07)
- **posts**: Lettura dello screen, transizioni e dati di screen del workflow (03-T08)
- **cli**: Comandi posts create, comment e get-for-create|edit|copy (03-T10)
- **cli**: Posts edit, edit-custom-data e copy come patch con occToken letto o imposto (03-T11)
- **cli**: Posts edit-watchers, delete e mark-erasable con conferma (03-T12)
- **cli**: Posts workflow-screen, workflow-execute e workflow-edit-screen (03-T13)
- **cli**: Le patch dei post rimandano i riferimenti letti come id (03-T18)

### Fixes

- **cli**: Posts delete e mark-erasable riportano l'id del post richiesto (03-T19)

### Refactors

- **cli**: Helper di scrittura condivisi in cli/_write.py e messaggio del 409 con il nome della risorsa (03-T09)

## [0.10.0] - 2026-10-09

### CI

- **deps**: Bump the github-actions group across 1 directory with 8 updates
- Pre-commit verde su tutti i file (ruamel.yaml nel hook mypy, file generati esclusi dai fixer)

### Chores

- Processore structlog e handler di file con cookie e header sensibili (01-T03)
- La pagina Audit Logging dichiara le garanzie di redazione (01-C11) (01-T04)
- Integration test opt-in del ciclo di scrittura dei task (02-T10)
- **api**: Caratterizzazione dei rami TypeError di ResourceClient (02-T01)
- **skills**: Rimozione di new-version e allineamento di release e WORKFLOW al metodo sddpa

### Documentation

- Adozione del metodo spec-driven (sddpa 0.3.0)
- ADR 0001: apertura della superficie di scrittura verso Interacta
- Conferma di scopo e attori del PRD, con gli usi vibe coding e server MCP
- Spec 01: redazione di cookie e header sensibili nei log e nei hook
- Piano 01: redazione di cookie e header sensibili nei log e nei hook
- Task 01: redazione di cookie e header sensibili nei log e nei hook
- Garanzie di redazione per cookie e header sensibili (01-T04)
- PRD, RNF-001 precisato dalla spec 01 e conferma di RF-017, RF-018, RNF-001 (01-T05)
- Verifica 01 con il problema di tracciabilità di 01-C11 e riapertura di T04
- Verifica 01: redazione di cookie e header sensibili nei log e nei hook
- Spec 02: scrittura dei task: creazione, modifica, eliminazione
- Piano 02: scrittura dei task: creazione, modifica, eliminazione
- Task 02: scrittura dei task: creazione, modifica, eliminazione
- Scrittura dei task nelle pagine API e CLI, exit code 9, variabile per gli integration test (02-T09)
- **spec**: Tasks edit come patch dopo l'esito di T11 (02-C17, 02-C18, T13)
- PRD e CLAUDE.md per la spec 02 (02-T12)
- Verifica 02 con il problema di copertura di api/_base.py e riapertura di T01
- Verifica 02: scrittura dei task, creazione, modifica, eliminazione
- Chiusura documentale della release 0.9.4 (ROADMAP, spec legacy, PROGRESS)
- Release v0.10.0, riga di ROADMAP a shipped

### Features

- **api**: Utilità per le scritture (scadenza con fuso, corpo camelCase, PUT e DELETE nel client base) (02-T01)
- **tasks**: Occ_token nella lettura e façade TaskWriteResult per le risposte di scrittura (02-T02)
- **tasks**: Creazione di un task su un post (create, create_raw) (02-T03)
- **tasks**: Modifica con occToken ed eliminazione di un task (edit, edit_raw, delete) (02-T04)
- **cli**: Exit code 9 per i conflitti, conferma delle operazioni distruttive e corpo da --json (02-T05)
- **cli**: Comando tasks create con flag e --json (02-T06)
- **cli**: Comando tasks edit con occToken letto o imposto (02-T07)
- **cli**: Comando tasks delete con conferma e --yes (02-T08)
- **cli**: Tasks edit conserva i campi non indicati rileggendo il task (02-T13)

### Fixes

- **security**: Redazione per nome degli header sensibili (01-T01)
- **security**: Redazione del valore dei cookie in Cookie e Set-Cookie (01-T02)
- **deps**: Aggiornamento del lock e PyJWT >= 2.15.0 per gli avvisi Dependabot

## [0.9.4] - 2026-09-12

### CI

- Publish releases to PyPI via trusted publishing

### Documentation

- Update CHANGELOG for v0.9.3
- Document the PyPI rewrite discontinuity and install path
- Update CHANGELOG for v0.9.4

## [0.9.3] - 2026-09-12

### Chores

- Release v0.9.3 — flip ROADMAP to shipped, freeze spec header

### Documentation

- Update CHANGELOG for v0.9.2
- Add the v0.9.3 security-hardening spec and ROADMAP row
- Log M25 in PROGRESS.md

### Fixes

- **security**: Redact response bodies and headers inside the transport
- **security**: Scope the token-cache key to the tenant

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


