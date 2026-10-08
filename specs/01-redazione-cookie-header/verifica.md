# Verifica 01 – Redazione di cookie e header sensibili nei log e nei hook

Data: 2026-10-08
Commit verificato: `df4e936` sul branch `m27_redazione_cookie_header` (task T01–T05, commit
`859b61e`, `1129894`, `6c45645`, `4c3dd5f`, `df4e936`)
Esito: **un problema di tracciabilità** (01-C11), vedi in fondo. La spec resta `approvata`.

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
| 01-C11 | **nessun test con marker e nessuna voce in "Verifica manuale"**. Controlli eseguiti qui: `uv run mkdocs build --strict` verde, `tests/unit/test_docs_snippets.py` 36 verdi, `grep -c "Set-Cookie\|Proxy-Authorization" docs/logging.md` → 2 | **problema di tracciabilità** |

Nota: in T03 i test di 01-C09 sono stati provati rossi con `logging.py` riportato a `b9ffe46`; in
T01 e T02 i test sono stati scritti e visti rossi prima del codice (16 e 19 rossi, i secondi
comprensivi di 8 test preesistenti che un primo isolamento imperfetto dello stato globale di
structlog faceva fallire, poi corretto con un fixture).

Nessun marker cita criteri inesistenti. I test preesistenti senza marker non sono un problema.

## Controlli automatici

| Controllo | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (104 file) |
| `uv run mypy src` | verde (52 file) |
| `uv run pytest -m "not integration and not contract"` | verde: 750 test (+33 rispetto alla partenza), 67 snapshot |
| `uv run pytest -m contract` | verde (87) |
| `uv run mkdocs build --strict` (aggiuntivo) | verde |
| `uv run pre-commit run --all-files` (aggiuntivo) | **rosso**, hook `mypy`: `src/pynteracta/cli/_common.py:232` `Cannot find implementation or library stub for module named "ruamel.yaml"`. Preesistente alla spec: il file non è toccato, l'import c'è dal 2026-06-08 (`f41b02e`) e `.pre-commit-config.yaml` (2026-05-30) non ha `ruamel.yaml` tra le `additional_dependencies` del hook. Non misurato dalla linea di partenza (pre-commit non è un controllo bloccante). |

Controlli a cricchetto: nessuno configurato.

## Copertura

Comando: `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`.

| Ambito | Copertura | Soglia | Esito |
|---|---|---|---|
| Totale | **93,18 %** (3865/4148 righe) | ≥ 85 % e ≥ 93,15 % (partenza) | ok |
| `src/pynteracta/logging.py` (toccato) | **94 %** (101/107) | ≥ 85 % | ok |

Righe scoperte di `logging.py`: 151 (ramo `authorization` di `redaction_processor` per campi
stringa), 164 (`get_logger`), 257 (renderer console), 334–347 (formatter `audit_raw` su file): tutte
preesistenti alla spec. Il codice nuovo (`_SENSITIVE_HEADER_*`, `_COOKIE_*`, `_redact_cookie_header`,
il ramo cookie di `redact_headers`) è coperto per intero.

## Regole non negoziabili

| Regola | Controllo | Esito |
|---|---|---|
| Token e segreti mai nei log | Il diff di `src/` non aggiunge chiamate ai logger, `print`, scritture su file. La redazione resta nel transport (nessuna modifica a `transport.py`); `audit_raw` non la aggira (01-C10). Chiude P-01. | rispettata |
| Cache del token con permessi stretti | Codice non toccato. | n/a |
| Segreti fuori dal repository | Nel diff dei test solo valori finti e riconoscibili (`2ec02ee10ef0ad90df56fbb07f2424ff`×2, `dXNlcjpwYXNz` = `user:pass`, `opaque-value-1234`, `val-1/2`); nessun file `.env`, `.secrets`, `audit.log` aggiunto. | rispettata |
| Soglie che non scendono | Copertura, controlli e regole di ruff/mypy invariati. | rispettata |
| Dati personali fuori dai log, con eccezione audit | Nessun nuovo dato personale trattato; i body seguono le regole di prima. | rispettata |
| Nessuna operazione ripetuta in automatico verso Interacta | Nessuna chiamata verso Interacta aggiunta. | n/a |

## Coerenza con spec, piano e PRD

- Il codice fa ciò che la spec descrive e niente di più: regola per nome (lista + pattern), cookie
  con valore redatto e nome/attributi conservati, fallback "in dubbio si redige"; `WWW-Authenticate`
  invariato; `--audit-raw` invariato.
- Scostamenti dal piano, dichiarati nei commit: il test del canale file di 01-C10 usa
  `setup_default_logging` invece di un handler agganciato a mano (senza, structlog non instrada
  sugli handler stdlib e il file resterebbe vuoto), con un fixture che ripristina la configurazione
  e spegne la cache dei logger; il test del file di 01-C09 emette da un logger structlog avvolto
  con `wrap_logger` sulla stessa catena, perché `extra=` di stdlib non entra nell'`event_dict`.
- "Requisiti nuovi" (RNF-001a) entrati nel PRD come testo di RNF-001 (T05, `df4e936`); RF-017,
  RF-018, RNF-001 portano la conferma del maintainer. Nessun cambiamento che richieda un ADR.

## Linea di partenza

Non aggiornata in questa verifica, perché la spec non si chiude. Alla chiusura: P-01 da segnare
chiusa dalla spec 01, copertura totale 93,15 % → 93,18 %, `logging.py` 93,41 % → 94 %.

## Debiti aperti della linea di partenza

- P-01 (`redact_headers` e `Set-Cookie`): **risolta dal codice di questa spec**, si chiude nella
  partenza quando la spec passa a `chiusa`.
- Nuovo, fuori dalla partenza: `pre-commit run --all-files` rosso sul hook mypy per `ruamel.yaml`
  (vedi sopra). Proposta: branch `bugfix_precommit_mypy_ruamel` che aggiunge `ruamel.yaml` alle
  `additional_dependencies` del hook (o allinea il hook a `uv run mypy src`); non riguarda questa spec.
- `cli/communities.py` al 53 % di copertura (dalla partenza).

## Problemi trovati

1. **01-C11 non è tracciato**: la spec dichiara "Verifica manuale: Nessuna" ma nessun test porta
   `# criterio: 01-C11`; il piano prevedeva "unitario + controllo in verifica" con un `grep`, che qui
   è stato eseguito e ha dato esito positivo, ma la regola della verifica vuole un test con marker o
   una voce in "Verifica manuale" con l'esito. **Proposta**: un test con marker `# criterio: 01-C11`
   in `tests/unit/test_docs_snippets.py` che legge `docs/logging.md` e verifica la presenza delle
   garanzie (`Set-Cookie`, `Proxy-Authorization`, `***REDACTED***` nell'esempio di
   `audit.response`), così il criterio resta dimostrato a ogni esecuzione; da aggiungere a T04 in
   `tasks.md` (riaperto) ed eseguire con `/sddpa:implementa 01 T04`, poi rilanciare `/sddpa:verifica 01`.
