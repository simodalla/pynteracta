# Piano 07 – I token di concorrenza ottimistica passano in chiaro nei body redatti

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Tutto il lavoro sta in `redact_body()` di `src/pynteracta/logging.py`, l'unico punto da cui i body
passano verso hook (`RequestInfo.body`, `ResponseInfo.body`), eventi `audit.request` /
`audit.response` (console e file) e processore structlog (chiave `body`). Oggi una chiave è
sensibile se il suo nome contiene una parola del regex `_SENSITIVE_KEY_RE`; si aggiunge, **prima**
di quel confronto, un elenco chiuso di nomi esatti (confronto in minuscolo) che non sono segreti:
la famiglia occ del swagger e le sue grafie snake_case. Il transport e il processore non cambiano:
chiamano già la funzione in entrambe le direzioni, quindi i tre canali ereditano l'eccezione
insieme. I test si scrivono prima e devono essere rossi sul codice attuale (quelli di 07-C01,
07-C02, 07-C04, 07-C05, 07-C06, 07-C07 e 07-C08), mentre quello di regressione (07-C03) è verde già
oggi e lo si annota; poi la correzione li porta tutti a verde senza toccare i test esistenti.
Chiusura: `docs/logging.md`, PRD (RNF-001b e conferma di §6), riga `0.13.1 ⏳ M33` in ROADMAP
all'apertura e, con `/sddpa:verifica`, M33 in PROGRESS. Release: patch 0.13.1 con la skill
`release` dopo il merge, come deciso nella spec.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `ROADMAP.md` | modificato (apertura) | riga `0.13.1 ⏳ M33`, "Audit readability: optimistic-concurrency tokens (`occToken` family) stay in clear in redacted bodies (patch)", link alla spec; nota "last used: M33" |
| `src/pynteracta/logging.py` | modificato | costante `_OCC_TOKEN_KEYS: frozenset[str]` con gli otto nomi in minuscolo (`occtoken`, `nextocctoken`, `screenocctoken`, `nextscreenocctoken`, `occ_token`, `next_occ_token`, `screen_occ_token`, `next_screen_occ_token`) e commento in italiano sul perché; helper privato `_is_sensitive_key(name: str) -> bool` (`name.lower() not in _OCC_TOKEN_KEYS and _SENSITIVE_KEY_RE.search(name)`), usato da `redact_body()` al posto del confronto diretto con il regex; docstring di `redact_body` aggiornata con l'eccezione |
| `tests/unit/test_redaction.py` | modificato | `TestRedactBody`: 07-C01, 07-C02 (parametrizzato sulle dieci grafie, valori numero e stringa), 07-C03 (parametrizzato sulle sei chiavi che restano redatte), 07-C04 (forma di `edit_members` e di un form admin) |
| `tests/unit/test_logging.py` | modificato | `TestRedactionProcessorBodies` (classe nuova accanto a `TestRedactionProcessorHeaders`): 07-C06 sul processore e sull'handler di file |
| `tests/unit/test_transport.py` | modificato | 07-C05: scrittura sagomata come `users.edit` con i tre canali (hook, `capture_logs`, handler di file); 07-C07: variante con `setup_default_logging(audit=True, audit_raw=True)` |
| `tests/unit/test_docs_snippets.py` | modificato | 07-C08: `test_logging_page_states_redaction_guarantees` cerca anche `occToken` nella sezione "Redaction guarantees" |
| `docs/logging.md` | modificato | "Redaction guarantees": dopo il punto sulle chiavi dei body, l'eccezione dei token di concorrenza ottimistica (`occToken`, `nextOccToken`, `screenOccToken`, `nextScreenOccToken`) con il motivo (contatori di versione, non segreti; servono a leggere l'audit delle scritture) e la precisazione che ogni altra chiave con `token` resta redatta |
| `specs/prd.md` | modificato (chiusura) | RNF-001: frase "Dalla spec 07 i campi di concorrenza ottimistica … passano in chiaro per nome esatto (RNF-001b)"; §6 "Dati personali trattati": frase sugli `occToken` in chiaro nell'audit log e nota "Confermato dal maintainer il 2026-10-12 (spec 07), per la parte sull'audit log" |
| `PROGRESS.md` | modificato (verifica) | sezione M33 (Done / Decisions / Follow-ups); il follow-up di M31 sull'`occToken` è barrato con il rimando alla spec 07 |

Nessun altro file: `transport.py`, `hooks.py`, la CLI e i modelli restano come sono. Il swagger non
cambia.

## Modello dati e migrazioni

Nessuna modifica.

## Flussi

```
transport.request(method, path, json=…)
  ├─ req_body = redact_body(json)             (solo con audit_bodies)
  │     ──► audit.request (console, file), RequestInfo.body
  ├─ httpx.Client.request()
  └─ resp_body = redact_body(response.json()) (solo con audit_bodies)
        ──► audit.response (console, file), ResponseInfo.body

redact_body(body)
  ├─ dict: per ogni (k, v)
  │     _is_sensitive_key(k)  → "***REDACTED***"
  │     altrimenti            → redact_body(v)          (ricorsione: liste, dict annidati)
  ├─ list: redact_body su ogni elemento
  ├─ str:  redact_string (JWT, query sensibili)         (invariato)
  └─ altro: invariato

_is_sensitive_key(name)
  ├─ name.lower() in _OCC_TOKEN_KEYS   → False   (occToken, nextOccToken, screenOccToken,
  │                                               nextScreenOccToken e grafie snake_case)
  └─ altrimenti                        → _SENSITIVE_KEY_RE.search(name) is not None
                                                 (token|password|secret|privatekey|assertion|
                                                  jwt|signature|policy, come oggi)

redaction_processor(event_dict)
  └─ chiave "body" → redact_body(...)             (eredita l'eccezione senza modifiche)
```

Esempio: `users.edit` manda `{"occToken": 3, "firstname": "A", "resetUserCustomCredentialsCommand":
{"password": ["x"]}}` e riceve `{"userId": 1, "nextOccToken": 4}`; nei tre canali compaiono
`"occToken": 3` e `"nextOccToken": 4`, `password` è `***REDACTED***`. `userOccToken` non è
nell'elenco → il regex lo prende → redatto.

## Interfaccia

Nessuna: nessun comando, flag o messaggio nuovo. `--audit-raw` resta com'è.

## Configurazione

Nessuna variabile nuova.

## Sicurezza e dati personali

- **Token e segreti mai nei log**: la regola generale non si allenta: l'eccezione è un elenco chiuso
  di nomi esatti, confrontati in minuscolo, e vale solo per chiavi che non autenticano nulla
  (contatori di versione). `accessToken`, `portal_api_jwt_token*`, `password`, `signature`,
  `policy`, `myToken`, `userOccToken` restano redatti e 07-C03 lo fissa. L'esclusione sta prima
  del regex ma non lo modifica, così un nome nuovo del tenant che contiene `token` resta redatto
  finché una spec non lo aggiunge all'elenco.
- **In dubbio si redige** (spec 01): nessun suffisso, nessun pattern; solo nomi noti.
- **Dati personali**: nessun nuovo dato trattato; l'audit log con `audit_log_bodies` resta
  l'eccezione documentata a carico di chi lo abilita (§6 del PRD, confermata).
- **Segreti nei test**: valori finti e riconoscibili (`s3cret`, `fake-access-token`), mai un valore
  reale.
- **Soglie che non scendono**: `logging.py` è al 94,50 % (103/109): l'helper ha due rami, entrambi
  con test; il totale (95,18 %) non scende.

## Test di caratterizzazione

Nessuno: il comportamento attuale di `redact_body` (chiavi sensibili a ogni profondità, liste,
JWT nei valori, chiavi innocue invariate, `myToken` e `accessToken` redatte) è già fissato da
`TestRedactBody` in `test_redaction.py`, da `TestSensitiveKeyCoverage` in `test_logging.py`, da
`test_audit_sensitive_body_key_redacted` e `test_password_keys_redacted_in_audit_and_hooks` in
`test_transport.py`. L'unico comportamento attuale non fissato (l'`occToken` redatto) è proprio
quello che la spec cambia.

## Strategia di test

Ordine obbligato: i test di 07-C01…07-C08 si scrivono **prima** della modifica e si esegue la
suite per vederli rossi sul codice attuale (07-C03 è verde già oggi: è una regressione,
e lo si annota nel task); poi la correzione li porta a verde senza rompere i test esistenti, in
particolare `test_sensitive_key_redacted` con `myToken`.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 07-C01 | `test_redaction.py::TestRedactBody::test_occ_token_kept_password_redacted`: `redact_body({"occToken": 7, "password": "x"})` → `{"occToken": 7, "password": "***REDACTED***"}` | unitario |
| 07-C02 | `test_occ_token_family_kept`, parametrizzato sulle dieci grafie della spec × valori `12` e `"12"` → valore invariato | unitario |
| 07-C03 | `test_other_token_keys_still_redacted`, parametrizzato su `userOccToken`, `myToken`, `accessToken`, `nextPageToken`, `token`, `TOKEN` → `***REDACTED***` (verde già oggi, regressione) | unitario |
| 07-C04 | `test_occ_token_kept_in_edit_members_and_form_shapes`: la lista di `edit_members` e il form `{"data": {"occToken": 3, "screenOccToken": 2, "password": "x"}}` → `occToken` e `screenOccToken` a ogni livello, `password` redatta, il resto uguale all'input | unitario |
| 07-C05 | `test_transport.py::test_occ_token_in_clear_in_audit_and_hooks`: `respx` su `PUT admin/manage/users/5`, richiesta `{"occToken": 3, "firstname": "A", "password": "s3cret"}`, risposta `{"userId": 5, "nextOccToken": 4, "accessToken": "fake-access-token"}`; `_make_transport(audit=True, audit_bodies=True, hooks=_Capture())` con `build_audit_file_handler(tmp_path / "audit.log")` agganciato all'audit logger (stesso schema di `test_login_shaped_set_cookie_never_leaks_to_audit_file`) dentro `capture_logs()`; asserzioni: `audit.request["body"]["occToken"] == 3`, `audit.response["body"]["nextOccToken"] == 4`, stessi valori in `RequestInfo.body` / `ResponseInfo.body` e nelle righe JSON del file; `s3cret` e `fake-access-token` assenti da `repr(logs)`, dai body dei hook e dal file; pulizia dell'handler in `finally` | unitario |
| 07-C06 | `test_logging.py::TestRedactionProcessorBodies::test_processor_keeps_occ_token_redacts_token`: `redaction_processor(None, "info", {"body": {"occToken": 3, "token": "x"}})` → `{"occToken": 3, "token": "***REDACTED***"}`; `test_file_handler_keeps_occ_token_redacts_token`: `build_audit_file_handler(tmp)` sull'audit logger, evento con quel `body`, lettura della riga JSON (schema di `test_file_handler_redacts_cookie_and_api_key`) | unitario |
| 07-C07 | `test_transport.py::test_occ_token_in_clear_with_audit_raw`: `setup_default_logging(audit=True, audit_raw=True)` con `monkeypatch` su `_AUDIT_RAW_WARNED` e `caplog`, stessa richiesta di 07-C05 catturando lo stream dell'handler console dell'audit; asserzioni: `"occToken": 3` presente, avviso `audit.redaction_disabled` emesso; pulizia degli handler come in `test_login_shaped_set_cookie_never_leaks_with_audit_raw`. Oggi è rosso sull'`occToken` (il transport lo redige prima che il canale raw lo riceva) e verde sull'avviso; dopo la correzione fissa che il canale raw mostra l'`occToken` come gli altri e che l'avviso resta | unitario |
| 07-C08 | `test_docs_snippets.py::test_logging_page_states_redaction_guarantees` con il needle `occToken` nella sezione "Redaction guarantees"; `uv run mkdocs build --strict` nel task di documentazione e in `verifica` | unitario + controllo in verifica |

Ogni test porta il commento `# criterio: 07-Cmm` sulla riga sopra, come da configurazione.

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| Elenco chiuso `_OCC_TOKEN_KEYS` (frozenset di nomi in minuscolo) controllato prima del regex, in un helper `_is_sensitive_key` | Lookahead negativo dentro `_SENSITIVE_KEY_RE`; pattern `(?i).*occtoken$` | Leggibile, estensibile per nome, nessuna modifica al regex esistente; il suffisso è escluso dalla spec ("in dubbio si redige") |
| Otto grafie scritte per esteso | Normalizzare `_` e maiuscole e confrontare con quattro nomi | Il confronto resta `name.lower() in set`, senza trasformazioni che potrebbero far coincidere nomi non previsti |
| Nessuna modifica a `transport.py` né al processore | Eccezione applicata solo nell'audit | La spec vuole lo stesso comportamento sui tre canali; la redazione sta nel transport (RNF-001) |
| Test di 07-C05 con `build_audit_file_handler` agganciato a mano all'audit logger | `setup_default_logging(audit_file=…)` | Evita `structlog.configure()` globale nel test del transport, come nella spec 01; 07-C07 usa `setup_default_logging` perché è l'unico modo di ottenere il formatter raw |
| Commit del task di codice `fix(audit): …` | `feat:`; `fix(security):` | Decisione della spec: è una correzione di leggibilità dell'audit, non una funzione nuova né un fix di sicurezza; semantic-release calcola la patch 0.13.1 |
| Riga `0.13.1 ⏳ M33` in ROADMAP nel primo task | Riga alla release | Voce di checklist del progetto, come nelle spec precedenti |

## Rischi

- **Allentamento involontario della regola generale** (per esempio un confronto per sottostringa
  invece che per nome esatto) → 07-C03 fissa che `userOccToken`, `myToken`, `accessToken`,
  `nextPageToken` restano redatte; `test_sensitive_key_redacted` esistente resta nella suite.
- **Un nome nuovo del tenant con la stessa natura** (per esempio un futuro `entryOccToken`) → resta
  redatto, per scelta; si aggiunge all'elenco con una spec, non con un pattern.
- **Stato globale di logging nei test** (`setup_default_logging` in 07-C07 configura structlog e
  aggiunge handler) → pulizia esplicita degli handler e `monkeypatch` su `_AUDIT_RAW_WARNED`, come
  già fa `test_login_shaped_set_cookie_never_leaks_with_audit_raw`.
- **Test di 07-C05 che "passa" senza dimostrare nulla** → le asserzioni positive (`== 3`, `== 4`)
  devono essere rosse prima della correzione; il task lo verifica eseguendo i test prima del codice.
- **Copertura di `logging.py`** → i due rami dell'helper hanno ciascuno un test; `verifica`
  controlla che il file resti ≥ 85 % e che il totale non scenda sotto 95,18 %.
