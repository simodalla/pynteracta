# Verifica 07 – I token di concorrenza ottimistica passano in chiaro nei body redatti

Data: 2026-10-12
Commit verificato: `9f4a752` sul branch `m33_occtoken_audit` (spec `f3ffdcc`, piano `5090bda`,
task `dd6cce9`; T01 `b199b7f`, T02 `1a00753`, T03 `9f4a752`)
Esito: **nessun problema**. Spec chiusa.

## Task

3 su 3 spuntati; nessun task `manuale`.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 07-C01 | `test_redaction.py::TestRedactBodyOccTokens::test_occ_token_kept_password_redacted` | verde |
| 07-C02 | `test_redaction.py::TestRedactBodyOccTokens::test_occ_token_family_kept` (10 grafie × `int`, `str`) | verde |
| 07-C03 | `test_redaction.py::TestRedactBodyOccTokens::test_other_token_keys_still_redacted` (6 chiavi; verde anche prima della correzione: regressione) | verde |
| 07-C04 | `test_redaction.py::TestRedactBodyOccTokens::test_occ_token_kept_in_edit_members_and_form_shapes` | verde |
| 07-C05 | `test_transport.py::test_occ_token_in_clear_in_audit_and_hooks`; `test_transport.py::test_occ_token_in_clear_in_audit_file` | verde |
| 07-C06 | `test_logging.py::TestRedactionProcessorBodies::test_processor_keeps_occ_token_redacts_token`; `test_logging.py::TestRedactionProcessorBodies::test_file_handler_keeps_occ_token_redacts_token` | verde |
| 07-C07 | `test_transport.py::test_occ_token_in_clear_with_audit_raw` | verde |
| 07-C08 | `test_docs_snippets.py::test_logging_page_states_redaction_guarantees`; `uv run mkdocs build --strict` | verde |

8 criteri su 8 con almeno un test; nessun marker cita un criterio inesistente. Prima della
correzione erano rossi tutti i test tranne quello di 07-C03, ciascuno per il motivo atteso
(`***REDACTED***` al posto dell'`occToken`, anche sul canale `--audit-raw`, perché la redazione
avviene nel transport); quello di 07-C08 era rosso prima della modifica della pagina.

## Controlli automatici

| Comando | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde |
| `uv run mypy src` | verde (60 file) |
| `uv run pytest -m "not integration and not contract"` | verde (1383 test) |
| `uv run pytest -m contract` | verde (201 test) |
| `uv run mkdocs build --strict` | verde |
| `uv run pre-commit run --all-files` | verde |

Nessun controllo a cricchetto configurato.

## Copertura

| Ambito | Linea di partenza | Ora |
|---|---|---|
| Totale | 95,18 % (5998/6302) | **95,18 %** (6003/6307 righe) |
| `logging.py` | 94,50 % (103/109) | **94,74 %** (108/114) |

File toccati dalla spec, soglia 85 %:

| File | Copertura | Righe scoperte |
|---|---|---|
| `logging.py` | 94,74 % | 196, 209, 302, 379-392 (preesistenti: chiave `authorization` nel processore, `get_logger`, renderer console, formatter raw del file); `_OCC_TOKEN_KEYS`, `_is_sensitive_key` e `redact_body` coperti per intero |

Unit test 1350 → 1383, contract test invariati (201). La linea di partenza è aggiornata.

## Regole non negoziabili

| Regola | Verifica | Esito |
|---|---|---|
| Token e segreti mai nei log | L'eccezione è un elenco chiuso di otto nomi esatti di contatori di versione, confrontati in minuscolo; il regex delle chiavi sensibili non cambia. 07-C03 fissa che `userOccToken`, `myToken`, `accessToken`, `nextPageToken`, `token` restano redatte; 07-C05 che password e access token non compaiono in nessuno dei tre canali; i test preesistenti su `accessToken`, `password`, `signature`, `policy` restano verdi. | rispettata |
| Cache del token con permessi stretti | Non toccata. | rispettata |
| Segreti fuori dal repository | Valori finti e riconoscibili nei test (`s3cret`, `fake-access-token`); nessun file segreto versionato. | rispettata |
| Soglie che non scendono | Copertura totale stabile (6003/6307 contro 5998/6302), `logging.py` in salita; regole di ruff e mypy invariate. | rispettata |
| Dati personali fuori dai log | Gli `occToken` non sono dati personali; nessun log nuovo. | rispettata |
| Nessuna operazione ripetuta in automatico | Non toccata: la spec cambia solo la redazione. | rispettata |

## Coerenza

- Il codice fa ciò che dicono spec e piano, e niente di più: una sola modifica in `redact_body`
  tramite `_is_sensitive_key`; transport, hook, processore structlog e CLI invariati.
- Scostamento dal piano, solo nei test: 07-C05 è diviso in due test, perché `capture_logs`
  sostituisce i processori structlog e il canale file non riceverebbe gli eventi; il test del
  file usa `_setup_audit_logging(audit_file=…)`, lo stesso schema del test di 01-C10 citato dal
  piano, invece di agganciare a mano `build_audit_file_handler`.
- Nessun ADR nuovo: la spec precisa RNF-001 senza contraddirlo. I "Requisiti nuovi" sono nel
  PRD (`9f4a752`): RNF-001b dentro RNF-001; la parte sull'audit log di §6 confermata.

## Debiti aperti della linea di partenza

Nessuna violazione `P-<mm>` aperta; nessun controllo a cricchetto. Copertura misurata.

## Problemi trovati

Nessuno.
