# Task 01 – Redazione di cookie e header sensibili nei log e nei hook

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si esegue il file di test e si
annota quali sono rossi sul codice attuale; poi si scrive il codice; il commit arriva con i cinque
controlli bloccanti verdi. Ogni test porta `# criterio: 01-Cmm` sulla riga sopra. Messaggi di commit
in Conventional Commits con descrizione in italiano.

## Elenco

### [x] T01 – Header redatti per nome in `redact_headers`

- Criteri: 01-C05, 01-C06, 01-C07, 01-C08
- Dipende da: nessuno
- Test: `tests/unit/test_redaction.py::TestRedactHeaders` — `test_auth_headers_redacted_by_name`
  (parametrizzato: `Authorization`, `authorization`, `Proxy-Authorization`, `PROXY-AUTHORIZATION`,
  valore `Basic dXNlcjpwYXNz`), `test_sensitive_header_names_redacted` (parametrizzato:
  `X-Api-Key`, `x-api-key`, `X_API_KEY`, `X-Auth-Token`, `X-Refresh-Token`, `X-Secret`,
  `X-Password`, anche con valore vuoto), `test_non_sensitive_headers_untouched` (`Content-Type`,
  `X-Request-Id`, `WWW-Authenticate: Bearer error="invalid_token"`, `Date`, `User-Agent`),
  `test_jwt_embedded_in_other_header_only_jwt_redacted` (`X-Custom: before eyJ… after`).
  Rossi prima del codice: i casi `Proxy-Authorization` e tutti quelli di 01-C06; verdi già oggi
  (regressioni): `Authorization`, 01-C07, 01-C08.
- Passi:
  1. Scrivere i quattro test; eseguire `uv run pytest tests/unit/test_redaction.py` e annotare i
     rossi attesi.
  2. In `src/pynteracta/logging.py` aggiungere `_SENSITIVE_HEADER_NAMES = {"authorization",
     "proxy-authorization"}` e `_SENSITIVE_HEADER_RE = re.compile(r"(?i)token|secret|password|api[-_]?key")`.
  3. In `redact_headers()` sostituire il ramo `k.lower() == "authorization"` con: nome
     (minuscolo) in `_SENSITIVE_HEADER_NAMES` o che corrisponde a `_SENSITIVE_HEADER_RE` →
     `_REDACTED`; altrimenti `redact_string(v)` come oggi. Aggiornare la docstring.
  4. Controlli bloccanti; commit `fix(security): redazione per nome degli header sensibili`.

### [x] T02 – Redazione del valore dei cookie in `Cookie` e `Set-Cookie`

- Criteri: 01-C01, 01-C02, 01-C03, 01-C04, 01-C10
- Dipende da: T01 (stesso ramo di `redact_headers`)
- Test: `tests/unit/test_redaction.py::TestRedactHeaders` —
  `test_set_cookie_value_redacted_attributes_kept` (`a=1; Secure; HttpOnly` →
  `a=***REDACTED***; Secure; HttpOnly`; variante `a=; Path=/`),
  `test_set_cookie_joined_pair_with_expires_comma` (valore unito ottenuto nel test da
  `httpx.Headers([...]).items()`, con `Expires=Thu, 02-Jul-2026 16:06:04 GMT`: entrambi i valori
  redatti, nomi e attributi intatti, `Expires` intatto), `test_cookie_request_header_all_values_redacted`
  (`a=1; b=2`), `test_cookie_header_without_equals_fully_redacted` (parametrizzato su `Cookie` e
  `Set-Cookie`, valori `garbage` e `a="x,y"`).
  `tests/unit/test_transport.py::test_login_shaped_set_cookie_never_leaks` — risposta `respx` con
  `Set-Cookie: interacta_auth_refresh_token=<64 hex finti>; Secure; HttpOnly; SameSite=Strict;
  Path=/portal/api/core/auth/refresh-token/; Expires=Thu, 02-Jul-2026 16:06:04 GMT`, transport con
  `audit=True` e hook di cattura; asserzioni: il valore non compare in `ResponseInfo.headers`,
  nell'evento `audit.response` di `capture_logs`, nel file scritto da `build_audit_file_handler`
  agganciato all'audit logger (pulizia degli handler alla fine); il nome del cookie e `Expires=Thu,
  02-Jul-2026 16:06:04 GMT` compaiono. `test_login_shaped_set_cookie_never_leaks_with_audit_raw`
  — `setup_default_logging(audit=True, audit_raw=True)` con `monkeypatch` su `_AUDIT_RAW_WARNED`
  e cattura dello stream dell'handler: il valore non compare; pulizia degli handler.
  Rossi prima del codice: tutti.
- Passi:
  1. Scrivere i test; eseguirli e annotare che sono tutti rossi sul codice di T01.
  2. In `logging.py` aggiungere `_COOKIE_ATTRIBUTES = {"expires", "max-age", "domain", "path",
     "samesite", "secure", "httponly", "partitioned", "priority"}` e la regex delle coppie
     `nome=valore` con il separatore che le precede (inizio, `,` o `;`).
  3. Aggiungere `_redact_cookie_header(name: str, value: str) -> str`: senza `=` o con `"` →
     `_REDACTED`; `cookie` → ogni coppia con valore `_REDACTED`; `set-cookie` → coppia all'inizio
     o dopo `,` → cookie; dopo `;` → cookie solo se il nome non è in `_COOKIE_ATTRIBUTES`;
     frammenti senza `=` invariati.
  4. In `redact_headers()` instradare i nomi `cookie` e `set-cookie` (minuscolo) sul helper, prima
     del ramo generico.
  5. Controlli bloccanti; commit `fix(security): redazione del valore dei cookie in Cookie e
     Set-Cookie (chiude P-01)`.

### [x] T03 – Processore structlog e handler di file dell'audit con header sensibili

- Criteri: 01-C09
- Dipende da: T02
- Test: `tests/unit/test_logging.py::TestRedactionProcessorHeaders` —
  `test_processor_redacts_cookie_and_api_key` (`redaction_processor(None, "info", {"event": "x",
  "headers": {"Set-Cookie": "a=1; Secure", "X-Api-Key": "k"}})` → `a=***REDACTED***; Secure` e
  `***REDACTED***`), `test_file_handler_redacts_cookie_and_api_key` (`build_audit_file_handler(tmp)`
  sull'audit logger, evento con quegli `headers`, rilettura del file JSON-lines, schema di
  `test_redaction_applied_to_file`, pulizia degli handler).
  Il comportamento è ereditato da T02: per dimostrare che i test lo verificano davvero, eseguirli
  anche con `src/pynteracta/logging.py` riportato temporaneamente alla versione precedente a T01
  (`git checkout b9ffe46 -- src/pynteracta/logging.py`, test rossi, poi `git checkout HEAD --
  src/pynteracta/logging.py`), e annotarlo nel commit.
- Passi:
  1. Scrivere i due test; verificarli verdi su HEAD e rossi sulla versione `b9ffe46` di
     `logging.py`, poi ripristinare il file.
  2. Controlli bloccanti; commit `test: processore structlog e handler di file con cookie e header
     sensibili (01-C09)`.

### [x] T04 – Pagina "Audit Logging" del sito

- Criteri: 01-C11
- Dipende da: T02
- Test: nessun test automatico sul contenuto; verifica con `uv run mkdocs build --strict`,
  `uv run pytest tests/unit/test_docs_snippets.py` e `grep -n "Set-Cookie\|Proxy-Authorization"
  docs/logging.md` (entrambe le stringhe presenti).
- Passi:
  1. In `docs/logging.md`, "What is captured": `Response headers` → `Redacted response headers`.
  2. "Log format": nell'esempio di `audit.response` mostrare `"headers": {"content-type": "…",
     "set-cookie": "interacta_auth_refresh_token=***REDACTED***; Secure; HttpOnly; …"}`.
  3. "Redaction guarantees": due punti nuovi — header redatti per nome (`Authorization`,
     `Proxy-Authorization`, nomi con `token`/`secret`/`password`/`api-key`, intero valore) e cookie
     (`Cookie`/`Set-Cookie`: valore di ogni cookie sostituito, nome e attributi conservati; valore
     non analizzabile → tutto redatto); nota "since 0.9.5" per coerenza con la nota v0.9.3.
  4. Verifiche del punto "Test"; commit `docs: garanzie di redazione per cookie e header sensibili`.

### [ ] T05 – Chiusura: PRD

- Criteri: nessuno nuovo (chiusura della spec: "Requisiti nuovi" e conferme)
- Dipende da: T04
- Test: nessuno; verifica con la rilettura del diff di `specs/prd.md` e il controllo che ogni
  link risolva.
- Passi:
  1. In `specs/prd.md` §4 riscrivere RNF-001 con il testo di RNF-001a della spec (cookie e header
     per nome), citando la spec 01; togliere l'id provvisorio.
  2. Nel PRD annotare la conferma di RF-017, RF-018 e RNF-001 (2026-10-08, spec 01) accanto a
     ciascun requisito, lasciando "Da confermare" sulle sezioni §3 e §4 nel loro insieme.
  3. Aggiungere la riga alla "Storia del documento".
  4. Commit `docs: PRD, RNF-001 precisato dalla spec 01 e conferma di RF-017, RF-018, RNF-001`.

La riga `0.9.5 ⏳ M27` in `ROADMAP.md` è già stata aperta con la spec; la sezione M27 in
`PROGRESS.md` e la chiusura di P-01 in `specs/00-partenza/partenza.md` le scrive `/sddpa:verifica`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 01-C01 | T02 |
| 01-C02 | T02 |
| 01-C03 | T02 |
| 01-C04 | T02 |
| 01-C05 | T01 |
| 01-C06 | T01 |
| 01-C07 | T01 |
| 01-C08 | T01 |
| 01-C09 | T03 |
| 01-C10 | T02 |
| 01-C11 | T04 |
