# Piano 01 – Redazione di cookie e header sensibili nei log e nei hook

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Tutto il lavoro sta in `redact_headers()` di `src/pynteracta/logging.py`, l'unico punto da cui gli
header passano verso hook (`RequestInfo`, `ResponseInfo`), eventi `audit.request` /
`audit.response` e processore structlog: oggi riconosce solo `Authorization` e i JWT. Le si
aggiungono due regole: una **per nome** (lista fissa più pattern, intero valore sostituito) e una
**per i cookie** (`Cookie`, `Set-Cookie`: valore di ogni cookie sostituito, nome e attributi
conservati, con sostituzione regex sul valore così come httpx lo presenta, anche quando più
`Set-Cookie` sono uniti da `, `). Il transport e il processore non cambiano: chiamano già la
funzione per entrambe le direzioni. I test si scrivono prima e devono essere rossi sul codice
attuale (regola del maintainer per i test di sicurezza), poi la correzione li porta a verde.
Chiusura: `docs/logging.md`, PRD (RNF-001a e conferme) e, con `/sddpa:verifica`, P-01 nella linea
di partenza e M27 in PROGRESS.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `src/pynteracta/logging.py` | modificato | `redact_headers()`: regola per nome e redazione dei cookie; costanti `_SENSITIVE_HEADER_NAMES`, `_SENSITIVE_HEADER_RE`, `_COOKIE_ATTRIBUTES`, regex delle coppie; helper privato `_redact_cookie_header(name, value)` |
| `tests/unit/test_redaction.py` | modificato | test unitari di `redact_headers`: 01-C01…01-C08 e casi limite |
| `tests/unit/test_logging.py` | modificato | 01-C09: processore structlog e handler di file dell'audit con `headers` sensibili |
| `tests/unit/test_transport.py` | modificato | 01-C10: risposta sagomata come il login reale, tre canali, anche con `audit_raw` |
| `docs/logging.md` | modificato | 01-C11: "What is captured", esempio di `audit.response`, "Redaction guarantees" |
| `specs/prd.md` | modificato | RNF-001 precisato (RNF-001a); nota di conferma di RF-017, RF-018, RNF-001 |

Nessun altro file: `transport.py` e `hooks.py` restano come sono.

## Modello dati e migrazioni

Nessuna modifica.

## Flussi

```
transport.request()
  ├─ headers = _build_headers()                      (User-Agent, Authorization)
  ├─ redact_headers(headers)  ──► RequestInfo.headers, audit.request
  ├─ httpx.Client.request()
  ├─ redact_headers(response.headers)                (httpx.Headers: Set-Cookie uniti con ", ")
  │     per ogni (nome, valore):
  │       nome in {authorization, proxy-authorization}
  │         o nome ~ /token|secret|password|api[-_]?key/i   → "***REDACTED***"
  │       nome in {cookie, set-cookie}                       → _redact_cookie_header(nome, valore)
  │       altrimenti                                         → redact_string(valore)   (JWT, come oggi)
  └─ ──► ResponseInfo.headers, audit.response

_redact_cookie_header(nome, valore)
  ├─ nessun "=" nel valore, oppure contiene '"'          → "***REDACTED***" (in dubbio si redige)
  ├─ nome == "cookie": ogni coppia nome=valore            → nome=***REDACTED***
  └─ nome == "set-cookie": sostituzione regex delle coppie
        coppia all'inizio o preceduta da ","              → cookie: valore redatto
        coppia preceduta da ";" con nome ∉ attributi noti → cookie: valore redatto
        coppia preceduta da ";" con nome ∈ attributi noti → attributo: invariata
        frammento senza "=" (es. " 02-Jul-2026 16:06:04 GMT" dopo "Expires=Thu")
                                                          → invariato
redaction_processor(event_dict)
  └─ chiave "headers" → redact_headers(...)               (eredita le regole senza modifiche)
```

Attributi noti di `Set-Cookie` (confronto senza maiuscole): `expires`, `max-age`, `domain`,
`path`, `samesite`, `secure`, `httponly`, `partitioned`, `priority`. Il pattern sul nome usa
`api[-_]?key` così `X-Api-Key` e `x_api_key` sono equivalenti; `token`, `secret`, `password` non
hanno separatori.

## Interfaccia

Nessuna: nessun comando, flag o messaggio nuovo. `--audit-raw` resta com'è.

## Configurazione

Nessuna variabile nuova.

## Sicurezza e dati personali

- **Token e segreti mai nei log**: la redazione resta nel transport, prima di hook e logging, e
  si estende a cookie e header per nome; `audit_raw` non la aggira perché il valore non entra mai
  nell'`event_dict`. Chiude P-01.
- **In dubbio si redige**: valore senza `=` o con virgolette → intero valore sostituito; un errore
  di riconoscimento non produce mai un passaggio in chiaro.
- **Dati personali**: nessun nuovo dato trattato; i body seguono le regole di oggi.
- **Segreti nei test**: valori finti e riconoscibili (`2ec0…` ripetuto, `abc123`,
  `Basic dXNlcjpwYXNz` = `user:pass`), mai un valore reale; l'`audit.log` locale del maintainer non
  si usa come fixture.
- **Soglie che non scendono**: `logging.py` è al 93,4 %; i test nuovi coprono ogni ramo del helper.

## Test di caratterizzazione

Nessuno: il comportamento attuale di `redact_headers` (Authorization, JWT ovunque, header
innocui invariati, dizionario nuovo) è già fissato da `TestRedactHeaders` in
`test_redaction.py`, dal processore in `test_logging.py` e dal transport in
`test_response_headers_are_redacted_in_both_channels`. L'unico comportamento attuale non fissato
(il cookie `sid=abc123` passa in chiaro) è proprio quello che la spec cambia.

## Strategia di test

Ordine obbligato: i test di 01-C01…01-C10 si scrivono **prima** della modifica e si esegue la
suite per vederli rossi sul codice attuale (01-C05 con `Authorization` e 01-C07/01-C08 sono verdi
già oggi: sono regressioni, e lo si annota); poi la correzione li porta a verde senza rompere i
test esistenti.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 01-C01 | `test_redaction.py::TestRedactHeaders::test_set_cookie_value_redacted_attributes_kept`: `{"Set-Cookie": "a=1; Secure; HttpOnly"}` → `"a=***REDACTED***; Secure; HttpOnly"`; più il test di transport di 01-C10 che verifica hook e `audit.response` | unitario |
| 01-C02 | `test_set_cookie_joined_pair_with_expires_comma`: valore unito come lo produce httpx (ottenuto da `httpx.Headers([...]).items()` nel test, così il formato è quello vero), con `Expires=Thu, 02-Jul-2026 16:06:04 GMT` → entrambi i valori redatti, nomi e tutti gli attributi presenti, `Expires=Thu, 02-Jul-2026 16:06:04 GMT` intatto | unitario |
| 01-C03 | `test_cookie_request_header_all_values_redacted`: `{"Cookie": "a=1; b=2"}` → `"a=***REDACTED***; b=***REDACTED***"`; più un test di transport con hook di richiesta che inietta `Cookie` tramite `redact_headers` sul mapping di richiesta (`RequestInfo.headers`, `audit.request`) | unitario |
| 01-C04 | `test_cookie_header_without_equals_fully_redacted` (parametrizzato su `Cookie` e `Set-Cookie`): `"garbage"` → `"***REDACTED***"`; variante con virgolette `a="x,y"` → tutto redatto | unitario |
| 01-C05 | `test_auth_headers_redacted_by_name` parametrizzato su `Authorization`, `authorization`, `Proxy-Authorization`, `PROXY-AUTHORIZATION` con valore `Basic dXNlcjpwYXNz` → `***REDACTED***` | unitario |
| 01-C06 | `test_sensitive_header_names_redacted` parametrizzato su `X-Api-Key`, `x-api-key`, `X_API_KEY`, `X-Auth-Token`, `X-Refresh-Token`, `X-Secret`, `X-Password`, anche con valore vuoto → `***REDACTED***` | unitario |
| 01-C07 | `test_non_sensitive_headers_untouched`: `Content-Type`, `X-Request-Id`, `WWW-Authenticate: Bearer error="invalid_token"`, `Date`, `User-Agent` → invariati (estende `test_non_sensitive_headers_preserved`) | unitario |
| 01-C08 | `test_jwt_in_other_header_redacted` esistente, più `X-Custom: before eyJ… after` → solo il JWT sostituito | unitario |
| 01-C09 | `test_logging.py::TestRedactionProcessorHeaders::test_processor_redacts_cookie_and_api_key`: `redaction_processor({"headers": {"Set-Cookie": "a=1; Secure", "X-Api-Key": "k"}})` → valori attesi; `test_file_handler_redacts_cookie_and_api_key`: `build_audit_file_handler(tmp)` sull'audit logger, evento con quegli `headers`, lettura del file JSON-lines (stesso schema di `test_redaction_applied_to_file`) | unitario |
| 01-C10 | `test_transport.py::test_login_shaped_set_cookie_never_leaks` con `respx`: risposta con `Set-Cookie: interacta_auth_refresh_token=<64 hex finti>; Secure; HttpOnly; SameSite=Strict; Path=/portal/api/core/auth/refresh-token/; Expires=…` e `audit=True`; asserzioni: il valore non compare in `ResponseInfo.headers` del hook, nell'evento `audit.response` di `capture_logs`, né nel file scritto da `build_audit_file_handler` agganciato all'audit logger; variante con `setup_default_logging(audit=True, audit_raw=True)` più cattura dello stream: il valore non compare perché non entra mai nell'`event_dict`; pulizia degli handler come in `TestSetupDefaultLoggingAudit` | unitario |
| 01-C11 | `uv run mkdocs build --strict` e `tests/unit/test_docs_snippets.py` verdi; rilettura della pagina in `verifica` (la presenza delle righe nuove si controlla con `grep` su "Set-Cookie" e "Proxy-Authorization" in `docs/logging.md`, nel task di documentazione) | unitario + controllo in verifica |

Ogni test porta il commento `# criterio: 01-Cmm` sulla riga sopra, come da configurazione.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| Tutta la logica in `redact_headers()` (`logging.py`), con sostituzione regex sul valore unito | Redazione per-header nel transport con `httpx.Headers.multi_items()` e unione dopo | Un solo percorso, httpx-free, che vale per hook, audit e processore structlog, e per i mapping già uniti; nessuna modifica al transport. Limite noto e accettato: un secondo cookie chiamato come un attributo (`path=…`) dopo `;` resterebbe in chiaro, caso irreale |
| Regex sulle coppie `nome=valore` con la regola inizio/`,`/`;` e la lista degli attributi | `http.cookies.SimpleCookie` | Verificato: `SimpleCookie.load` sul valore unito da httpx restituisce zero cookie; la regex lavora anche sui frammenti dopo la virgola di `Expires` |
| Regola per nome come lista fissa + regex `(?i)token\|secret\|password\|api[-_]?key` | Solo lista fissa | Scelta della spec; simmetrica con `_SENSITIVE_KEY_RE` dei body |
| Valore con `"` o senza `=` → intero valore redatto | Tentare il parsing dei valori quotati | "In dubbio si redige" (spec); i valori quotati con virgole non sono delimitabili con certezza |
| `WWW-Authenticate` non in lista | Aggiungerla per prudenza | Il transport la legge per `auth.token_invalidated_by_server`; porta schema ed errore, non segreti (spec, caso limite) |
| Test di 01-C10 con `build_audit_file_handler` agganciato a mano all'audit logger | `setup_default_logging(audit_file=…)` | Evita `structlog.configure()` globale nel test del transport; la variante `audit_raw` usa `setup_default_logging` perché è l'unico modo di ottenere il formatter senza redazione, con pulizia degli handler |
| Commit del task di codice `fix(security): …` | `fix:` semplice | Scope già usato dalla v0.9.3; semantic-release calcola la patch |

## Rischi

- **Over-redaction di header legittimi** per via del pattern sul nome (per esempio un ipotetico
  `X-Token-Count`) → accettato dalla spec ("in dubbio si redige"); 01-C07 fissa l'elenco degli header
  comuni che devono restare invariati.
- **Formato dei cookie diverso da quello previsto** (valori quotati, virgole nel valore) → regola
  di fallback: intero valore redatto (01-C04); mai un passaggio in chiaro.
- **Test di 01-C10 che "passa" senza dimostrare nulla** (fixture che non assomiglia alla risposta
  reale) → la fixture riproduce esattamente la forma dell'`audit.log` locale (nome del cookie, flag,
  `Path`, `Expires` con virgola), con valore finto; e il test deve essere rosso prima della
  correzione.
- **Stato globale di logging nei test** (`setup_default_logging` configura structlog e aggiunge
  handler) → pulizia esplicita degli handler come già fanno i test esistenti; il test `audit_raw`
  resetta anche `_AUDIT_RAW_WARNED` con `monkeypatch`.
- **Copertura di `logging.py`** → i rami del helper (nessun `=`, virgolette, `Cookie`, `Set-Cookie`,
  attributo, frammento) hanno ciascuno un test; `verifica` controlla che il file resti ≥ 85 % e che
  il totale non scenda sotto 93,15 %.
