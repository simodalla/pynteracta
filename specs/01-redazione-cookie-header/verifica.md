# Verifica 01 – Redazione di cookie e header sensibili nei log e nei hook

Data: 2026-10-08
Commit verificato: `3a305e5` sul branch `m27_redazione_cookie_header` (task T01–T05: `859b61e`,
`1129894`, `6c45645`, `4c3dd5f`, `df4e936`, più `3a305e5` per il passo 5 di T04)
Esito: **nessun problema**. Spec chiusa.

Una prima verifica (`29b9fa4`) aveva trovato 01-C11 senza tracciabilità; T04 è stato riaperto e
chiuso con un test con marker. Questo rapporto la sostituisce.

## Task

5 su 5 spuntati; nessun task `manuale`.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 01-C01 | `tests/unit/test_redaction.py::TestRedactHeaders::test_set_cookie_value_redacted_attributes_kept`, `::test_set_cookie_empty_value_redacted_attributes_kept`; più 01-C10 (hook e `audit.response`) | verde |
| 01-C02 | `test_redaction.py::TestRedactHeaders::test_set_cookie_joined_pair_with_expires_comma` (valore unito prodotto da `httpx.Headers`) | verde |
| 01-C03 | `test_redaction.py::TestRedactHeaders::test_cookie_request_header_all_values_redacted` | verde |
| 01-C04 | `test_redaction.py::TestRedactHeaders::test_cookie_header_without_equals_or_quoted_fully_redacted` (4 casi) | verde |
| 01-C05 | `test_redaction.py::TestRedactHeaders::test_auth_headers_redacted_by_name` (4 casi) | verde |
| 01-C06 | `test_redaction.py::TestRedactHeaders::test_sensitive_header_names_redacted` (14 casi) | verde |
| 01-C07 | `test_redaction.py::TestRedactHeaders::test_non_sensitive_headers_untouched` | verde |
| 01-C08 | `test_redaction.py::TestRedactHeaders::test_jwt_embedded_in_other_header_only_jwt_redacted` | verde |
| 01-C09 | `tests/unit/test_logging.py::TestRedactionProcessorHeaders::test_processor_redacts_cookie_and_api_key`, `::test_file_handler_redacts_cookie_and_api_key` | verde |
| 01-C10 | `tests/unit/test_transport.py::test_login_shaped_set_cookie_never_leaks_to_hooks_and_audit_event`, `::test_login_shaped_set_cookie_never_leaks_to_audit_file`, `::test_login_shaped_set_cookie_never_leaks_with_audit_raw` | verde |
| 01-C11 | `tests/unit/test_docs_snippets.py::test_logging_page_states_redaction_guarantees`; più `uv run mkdocs build --strict` verde | verde |

Ogni test è stato visto rosso prima del codice che lo fa passare (T01: 16 rossi; T02: 19; T03 e
il passo 5 di T04: rossi con `logging.py` o `docs/logging.md` riportati alla versione precedente).
Nessun marker cita criteri inesistenti; i test preesistenti senza marker non sono un problema.

## Controlli automatici

| Controllo | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (104 file) |
| `uv run mypy src` | verde (52 file) |
| `uv run pytest -m "not integration and not contract"` | verde: 751 test (+34 rispetto alla partenza), 67 snapshot |
| `uv run pytest -m contract` | verde (87) |
| `uv run mkdocs build --strict` (aggiuntivo) | verde |
| `uv run pre-commit run --files <file della spec>` (aggiuntivo) | verde: tutti gli hook passano sui 9 file toccati |
| `uv run pre-commit run --all-files` (aggiuntivo) | rosso su tre hook, **tutti su file non toccati dalla spec e preesistenti**: `end-of-file-fixer` e `trailing-whitespace` su `.gitignore`, `CHANGELOG.md` e dieci snapshot `tests/unit/__snapshots__/*.ambr`; `mypy` su `src/pynteracta/cli/_common.py:232` (`ruamel.yaml` manca tra le `additional_dependencies` del hook, import presente dal 2026-06-08). I file toccati dai fixer sono stati ripristinati. Debito registrato sotto. |

Controlli a cricchetto: nessuno configurato.

## Copertura

Comando: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`.

| Ambito | Copertura | Soglia | Esito |
|---|---|---|---|
| Totale | **93,18 %** (3865/4148 righe) | ≥ 85 % e ≥ 93,15 % (partenza) | ok |
| `src/pynteracta/logging.py` (toccato) | **94,39 %** (101/107) | ≥ 85 % | ok |

Righe scoperte di `logging.py`: 151 (ramo `authorization` di `redaction_processor` per campi
stringa), 164 (`get_logger`), 257 (renderer console), 334–347 (formatter `audit_raw` su file): tutte
preesistenti. Il codice nuovo (`_SENSITIVE_HEADER_*`, `_COOKIE_*`, `_redact_cookie_header`, il ramo
cookie di `redact_headers`) è coperto per intero.

## Regole non negoziabili

| Regola | Controllo | Esito |
|---|---|---|
| Token e segreti mai nei log | Il diff di `src/` non aggiunge chiamate ai logger, `print`, scritture su file. La redazione resta nel transport (`transport.py` non modificato); `audit_raw` non la aggira (01-C10). **Chiude P-01.** | rispettata |
| Cache del token con permessi stretti | Codice non toccato. | n/a |
| Segreti fuori dal repository | Nel diff dei test solo valori finti e riconoscibili (`2ec02ee10ef0ad90df56fbb07f2424ff`×2, `dXNlcjpwYXNz` = `user:pass`, `opaque-value-1234`, `val-1/2`); nessun file `.env`, `.secrets`, `audit.log` aggiunto. | rispettata |
| Soglie che non scendono | Copertura, controlli e regole di ruff/mypy invariati. | rispettata |
| Dati personali fuori dai log, con eccezione audit | Nessun nuovo dato personale trattato. | rispettata |
| Nessuna operazione ripetuta in automatico verso Interacta | Nessuna chiamata verso Interacta aggiunta. | n/a |

## Coerenza con spec, piano e PRD

- Il codice fa ciò che la spec descrive e niente di più: regola per nome (lista + pattern), cookie
  con valore redatto e nome/attributi conservati, fallback "in dubbio si redige"; `WWW-Authenticate`
  invariato; `--audit-raw` invariato.
- Scostamenti dal piano, dichiarati nei commit: il test del canale file di 01-C10 usa
  `setup_default_logging` (senza, structlog non instrada sugli handler stdlib e il file resterebbe
  vuoto), con un fixture che ripristina la configurazione e spegne la cache dei logger; il test del
  file di 01-C09 emette da un logger structlog avvolto con `wrap_logger` sulla stessa catena,
  perché `extra=` di stdlib non entra nell'`event_dict`; 01-C11 ha un test con marker invece del
  solo controllo in verifica.
- "Requisiti nuovi" (RNF-001a) entrati nel PRD come testo di RNF-001 (`df4e936`); RF-017, RF-018,
  RNF-001 portano la conferma del maintainer. Nessun cambiamento che richieda un ADR.

## Linea di partenza

Aggiornata (`specs/00-partenza/partenza.md`): P-01 chiusa; copertura totale 93,15 % → 93,18 %,
`logging.py` 93,41 % → 94,39 %; unit test 717 → 751.

## Debiti aperti

- Nessuna violazione `P-<mm>` aperta nella linea di partenza.
- `cli/communities.py` al 53 % di copertura (dalla partenza).
- Fuori dalla partenza, emerso qui: `pre-commit run --all-files` rosso su `end-of-file-fixer`,
  `trailing-whitespace` (`.gitignore`, `CHANGELOG.md`, snapshot `.ambr`) e `mypy` (`ruamel.yaml`
  mancante nel hook). Proposta: branch `bugfix_precommit_hooks` che aggiunge `ruamel.yaml` alle
  `additional_dependencies` (o allinea il hook a `uv run mypy src`) e lascia passare i fixer sui tre
  gruppi di file; gli snapshot vanno rigenerati con `syrupy` perché il contenuto conti, non solo gli
  spazi.

## Problemi trovati

Nessuno.
