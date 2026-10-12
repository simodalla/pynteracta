# Task 07 – I token di concorrenza ottimistica passano in chiaro nei body redatti

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (`occToken` atteso in chiaro, trovato `***REDACTED***`); poi il codice;
il commit arriva con i cinque controlli bloccanti verdi. Ogni test porta `# criterio: 07-Cmm`
sulla riga sopra. Messaggi di commit in Conventional Commits con descrizione in italiano.
Valori finti dei test (dal piano): `occToken` `3` e `7`, `nextOccToken` `4`, `screenOccToken`
`2`, password `s3cret`, access token `fake-access-token`, utente `5`.

## Elenco

### [x] T01 – Riga di ROADMAP

- Criteri: nessuno (voce di checklist del progetto)
- Dipende da: nessuno
- Test: nessuno; si verifica con `uv run mkdocs build --strict` verde e la rilettura della riga.
- Passi:
  1. `ROADMAP.md`: riga `0.13.1 | Audit readability: optimistic-concurrency tokens (occToken
     family) stay in clear in redacted bodies (patch) | M33 | ⏳ In progress |
     specs/07-occtoken-audit/spec.md`; nota "last used: M33".
  2. Commit `docs: riga 0.13.1 in ROADMAP per la spec 07 (07-T01)`.

### [x] T02 – Eccezione della famiglia occ in `redact_body`

- Criteri: 07-C01, 07-C02, 07-C03, 07-C04, 07-C05, 07-C06, 07-C07
- Dipende da: T01
- Test:
  - `tests/unit/test_redaction.py::TestRedactBody`: `test_occ_token_kept_password_redacted`
    (07-C01), `test_occ_token_family_kept` (07-C02, dieci grafie × `12` e `"12"`),
    `test_other_token_keys_still_redacted` (07-C03, verde già prima: regressione),
    `test_occ_token_kept_in_edit_members_and_form_shapes` (07-C04);
  - `tests/unit/test_logging.py::TestRedactionProcessorBodies`: processore e handler di file
    (07-C06);
  - `tests/unit/test_transport.py`: `test_occ_token_in_clear_in_audit_and_hooks` (07-C05, tre
    canali, `s3cret` e `fake-access-token` assenti) e `test_occ_token_in_clear_with_audit_raw`
    (07-C07, avviso emesso, `occToken` in chiaro).
- Passi:
  1. Scrivere i test sopra; eseguirli e annotare nel commit quali sono rossi (tutti tranne
     07-C03) e perché.
  2. `src/pynteracta/logging.py`: `_OCC_TOKEN_KEYS` (otto nomi in minuscolo, commento in
     italiano sul perché), helper `_is_sensitive_key(name)`, `redact_body` lo usa; docstring
     aggiornata.
  3. Test verdi, compresi gli esistenti (`test_sensitive_key_redacted` con `myToken`,
     `TestSensitiveKeyCoverage`); controlli bloccanti e copertura di `logging.py` ≥ 94,50 %.
  4. Commit `fix(audit): occToken e varianti in chiaro nei body redatti di audit log e hook
     (07-T02)`.

### [ ] T03 – Chiusura: sito, PRD

- Criteri: 07-C08
- Dipende da: T02
- Test: `tests/unit/test_docs_snippets.py::test_logging_page_states_redaction_guarantees` con il
  needle `occToken` (rosso prima della modifica della pagina); `uv run mkdocs build --strict`.
- Passi:
  1. Aggiungere il needle al test e vederlo rosso.
  2. `docs/logging.md`, "Redaction guarantees": l'eccezione dei token di concorrenza ottimistica
     con il motivo e la precisazione che ogni altra chiave con `token` resta redatta.
  3. `specs/prd.md`: RNF-001 con la frase della spec 07 (RNF-001b); §6 con gli `occToken` in
     chiaro nell'audit log e la nota di conferma del 2026-10-12 (spec 07).
  4. Test e `mkdocs build --strict` verdi, controlli bloccanti; commit `docs: garanzie di
     redazione e PRD per i token di concorrenza (07-T03)`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 07-C01 | T02 |
| 07-C02 | T02 |
| 07-C03 | T02 |
| 07-C04 | T02 |
| 07-C05 | T02 |
| 07-C06 | T02 |
| 07-C07 | T02 |
| 07-C08 | T03 |
