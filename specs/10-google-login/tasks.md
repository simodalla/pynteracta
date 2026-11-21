# Task 10 – Login Google integrato con rinnovo automatico

Stato: approvati
Spec: [spec.md](spec.md) · Piano: [plan.md](plan.md)

Regola comune a ogni task con codice: i test si scrivono prima, si eseguono e si annota che sono
rossi per il motivo giusto (modulo, funzione, campo o flag inesistente); poi il codice; il commit
arriva con i cinque controlli bloccanti verdi. Ogni test porta `# criterio: 10-Cmm` sulla riga
sopra. Messaggi di commit in Conventional Commits con descrizione in italiano (`test`,
`refactor`, `feat(config)`, `feat(auth)`, `feat(transport)`, `feat(cli)`, `build`, `docs`) e
l'id del task nella descrizione. Gli snapshot syrupy nuovi si generano con `--snapshot-update` e
si leggono nel diff prima del commit. Nessuna chiamata di rete e nessun browser reale: `respx`
con `assert_all_mocked=True`, `MemoryKeychain` e `FakeBrowser` di `tests/unit/google_fakes.py`.
Valori finti dei test e dei docs: `000000000000-example.apps.googleusercontent.com`,
`GOCSPX-example-not-a-secret`, `1//example-refresh-token`, `ya29.example-access-token`,
`mario.rossi@example.org`.

## Elenco

### [x] T01 – Test di caratterizzazione di login statico, logout e precedenza dei token

- Criteri: nessuno direttamente; fissa il comportamento che 10-C12 e 10-C16 devono conservare
- Dipende da: nessuno
- Test: `tests/unit/test_cli_auth.py`:
  `TestAuthLoginGoogle::test_static_login_writes_profile_before_validation`,
  `::test_static_login_without_profile_uses_default_when_current_is_default`,
  `TestAuthLogout::test_logout_unresolvable_profile_exits_1`,
  `::test_logout_google_profile_clears_profile_key`; `tests/unit/test_client.py`:
  `TestInteractaClientGoogleOAuth2::test_explicit_token_wins_over_profile_token`,
  `::test_explicit_provider_with_profile_token`.
- Passi:
  1. Scrivere i sei test contro il codice di oggi; devono essere verdi subito. Se uno è rosso,
     il piano descrive male il comportamento attuale: fermarsi e dirlo al maintainer.
  2. Eseguire `test_cli_write.py` e i test di `post_multipart` in `test_transport.py` e
     annotare che coprono già `read_password` e l'assenza del corpo (nessun test nuovo).
  3. Controlli bloccanti; commit `test: caratterizzazione di login statico, logout e
     precedenza dei token (10-T01)`.

### [x] T20 – Chiave di cache del token Google sull'indirizzo dell'API

Aggiunto il 2026-11-21 dopo T01 (vedi "Revisioni" della spec); si esegue subito dopo T01.

- Criteri: 10-C41
- Dipende da: T01
- Test: `tests/unit/test_cli_auth.py::TestAuthLogout::test_logout_google_removes_client_cache_file`
  (`auth whoami` con token Google e cache su file, poi `auth logout` → nessun file rimasto) e
  `::test_logout_google_removes_legacy_cache_file` (file scritto con la chiave vecchia →
  eliminato); `tests/unit/test_auth.py`: `GoogleOAuth2TokenManager` con `cache_api_base` usa
  `build_cache_key(cache_api_base, nome)`, senza resta la base del transport.
- Passi:
  1. Scrivere i test; rossi (il file resta; parametro inesistente).
  2. `auth.py`: parametro `cache_api_base` di `GoogleOAuth2TokenManager`;
     `legacy_google_cache_key(profile, profile_name)`.
  3. `client.py`: passa `cache_api_base=api_base`. `cli/auth.py::logout`: per i profili
     `google_oauth2` elimina anche la chiave vecchia.
  4. Controlli bloccanti; commit `fix(auth): il logout elimina la cache del token Google
     (10-T20)`.

### [x] T02 – `ConfigurationError` e campo `google_client_id`

- Criteri: prepara 10-C04 (RF-016a)
- Dipende da: nessuno
- Test: `tests/unit/test_exceptions.py`: `ConfigurationError` è una `InteractaError`;
  `tests/unit/test_cli_common.py`: `error_exit_code(ConfigurationError(...)) == 2`;
  `tests/unit/test_config.py`: `google_client_id` letto dal profilo, sovrascritto da
  `PYNTERACTA_GOOGLE_CLIENT_ID`, `None` se assente, profili esistenti ancora validi.
- Passi:
  1. Scrivere i test; rossi (classe e campo inesistenti).
  2. `exceptions.py`: `ConfigurationError`; `cli/_common.py`: voce in `_EXIT_MAP`.
  3. `config.py`: `Profile.google_client_id` e `_EnvSettings.google_client_id`.
  4. Controlli bloccanti; commit `feat(config): ConfigurationError e campo google_client_id
     (10-T02)`.

### [x] T03 – Scrittura del profilo e percorso del file in `config.py`

- Criteri: nessuno (spostamento senza cambio di comportamento, serve a T11)
- Dipende da: T01
- Test: `tests/unit/test_config.py`: `config_file_path` (argomento, `PYNTERACTA_CONFIG_FILE`,
  predefinito); `write_profile_fields` su file assente, su profilo nuovo (scrive `base_url` e
  `base_path`/`api_version` solo se non predefiniti), su profilo esistente (non tocca
  `base_url`, conserva i commenti). I test di `test_cli_auth.py`, compresi quelli di T01,
  restano verdi senza modifiche.
- Passi:
  1. Scrivere i test; rossi (funzioni inesistenti).
  2. `config.py`: `config_file_path` e `write_profile_fields`, con la logica di
     `_load_config_doc`, `_profile_table` e `_persist_connection`.
  3. `cli/auth.py` usa `write_profile_fields`; `cli/_common.config_path_from_state` delega a
     `config_file_path`; si tolgono le tre funzioni private.
  4. Controlli bloccanti; commit `refactor(config): scrittura del profilo in config.py
     (10-T03)`.

### [x] T04 – Profilo corrente come predefinito dei login e del client

- Criteri: 10-C39, 10-C40 (per la chiave di cache; la sessione arriva con T10)
- Dipende da: T03
- Test: `tests/unit/test_config.py`: `resolve_profile_name` (nome dato, `current_profile`,
  `default` senza file); `tests/unit/test_cli_auth.py::TestAuthLoginCurrentProfile`,
  parametrizzato su token statico e service account: con `current_profile = "prod"` e senza
  `--profile` scrive in `prod` e non crea `default`, con `--profile X` scrive in `X`;
  `tests/unit/test_client.py`: `InteractaClient()` con `current_profile = "prod"` usa la chiave
  di cache di `prod`.
- Passi:
  1. Scrivere i test; rossi (scrive in `default`; chiave di cache `default`).
  2. `config.py`: `resolve_profile_name`.
  3. `cli/auth.py::login`: `effective_profile = profile or resolve_profile_name(state.profile,
     state.config_file)`; il messaggio di esito nomina il profilo scritto.
  4. `client.py`: quando risolve da sé il profilo, `profile_name` diventa
     `resolve_profile_name(profile_name, config_file)`.
  5. Controlli bloccanti; commit `feat(auth): login e client usano il profilo corrente
     (10-T04)`.

### [x] T05 – Extra `google` e modulo `keychain`

- Criteri: 10-C05, 10-C06, 10-C37
- Dipende da: T02
- Test: `tests/unit/test_keychain.py`: `open_keychain` con `sys.modules["keyring"] = None` →
  `ConfigurationError` con `pynteracta[google]`; backend `fail`, `null` e uno fuori elenco
  rifiutati con il rimando al token statico; backend in elenco e chainer omogeneo accettati,
  chainer misto rifiutato; `get`/`set`/`delete` e nomi delle voci (`session_entry`,
  `client_secret_entry`); un errore di `keyring` diventa `ConfigurationError` senza il valore;
  `pyproject.toml` letto con `tomllib`: `keyring` solo in `optional-dependencies.google`; con
  `keyring` assente `import pynteracta.client` e `import pynteracta.cli` riescono.
- Passi:
  1. `pyproject.toml`: extra `google = ["keyring>=25"]`, `keyring` nel gruppo `dev`;
     `uv lock` e `uv sync`.
  2. Scrivere i test; rossi (modulo inesistente).
  3. `src/pynteracta/keychain.py` come nel piano, con intestazione SPDX e import pigro.
  4. `tests/unit/google_fakes.py`: `MemoryKeychain`; `conftest.py`: fixture `memory_keychain`.
  5. Controlli bloccanti; commit `feat(auth): extra google e accesso al portachiavi di sistema
     (10-T05)`.

### [x] T06 – `HttpTransport.request_external`

- Criteri: 10-C34 (parte del transport)
- Dipende da: nessuno
- Test: `tests/unit/test_transport.py::TestRequestExternal`: `POST` con `form` e `GET` con
  `bearer_token` verso un URL assoluto; `audit.request`/`audit.response` e gli hook ricevono
  metodo, URL e stato con `body is None`, con e senza `audit_bodies`; `Authorization` redatto;
  una risposta `400` torna al chiamante senza eccezione; `httpx.ConnectTimeout` e
  `httpx.ConnectError` → `TransportError` dopo una sola richiesta; `notify_error` chiama
  `hooks.on_error`.
- Passi:
  1. Scrivere i test; rossi (metodo inesistente).
  2. `transport.py`: `request_external` e `notify_error`, riusando `_emit_request`, `_send` ed
     `_emit_response` con `capture_body=False`.
  3. Prova di fallimento: passare temporaneamente `form` a `_emit_request`, verificare che i
     test sul corpo diventino rossi, ripristinare.
  4. Controlli bloccanti; commit `feat(transport): richieste esterne senza corpo in log, audit
     e hook (10-T06)`.

### [x] T07 – PKCE, indirizzo di consenso e listener su loopback

- Criteri: 10-C01, 10-C08, 10-C10, 10-C36 (parte di libreria)
- Dipende da: nessuno
- Test: `tests/unit/test_google_oauth.py`: `new_pkce` (challenge = SHA-256 base64url del
  verificatore, valori diversi a ogni chiamata); `build_auth_url` (id del client, `scope=email`
  soltanto, `S256`, `state`, redirect `http://127.0.0.1:<porta>`, `access_type=offline`,
  `prompt=consent`); `LoopbackReceiver`: socket su `127.0.0.1`, codice restituito con `state`
  giusto, `AuthenticationError` con `state` diverso, con `error=access_denied` e allo scadere
  del timeout, richiesta senza `code` ignorata con `404`, seconda connessione rifiutata dopo la
  prima risposta, socket chiuso dopo `wait`; la pagina di esito non contiene codice, `state` né
  token e `capfd` resta vuoto.
- Passi:
  1. `tests/unit/google_fakes.py`: `FakeBrowser` (richiesta `urllib` in un thread, con `join`).
  2. Scrivere i test; rossi (modulo inesistente).
  3. `src/pynteracta/google_oauth.py`: costanti, `new_pkce`, `build_auth_url`,
     `LoopbackReceiver` con `log_message` muto e chiusura in `finally`.
  4. Prova di fallimento per 10-C36: togliere temporaneamente la sovrascrittura di
     `log_message`, verificare che il test su `capfd` diventi rosso, ripristinare.
  5. Controlli bloccanti; commit `feat(auth): PKCE, indirizzo di consenso e listener su
     loopback (10-T07)`.

### [x] T08 – Chiamate a Google: token, userinfo, revoca

- Criteri: 10-C20, 10-C21 (parte di protocollo); prepara 10-C09, 10-C29
- Dipende da: T06, T07
- Test: `tests/unit/test_google_oauth.py`: `exchange_code` invia `grant_type`, `code`,
  `client_id`, `client_secret`, `redirect_uri`, `code_verifier` come form e restituisce access
  e refresh token; risposta senza `refresh_token` → `AuthenticationError`;
  `refresh_access_token` invia `grant_type=refresh_token`; `fetch_email` fa una `GET` con
  bearer e restituisce l'email o `None`; `revoke` invia `token`; `invalid_grant` e
  `invalid_client` → `AuthenticationError` con il codice nel messaggio e `response_body`
  limitato a `error` ed `error_description`; `500` → `ServerError` senza corpo; corpo non JSON
  → `AuthenticationError` generica; l'errore passa da `notify_error`.
- Passi:
  1. Risposte di Google per `respx` in `google_fakes.py`.
  2. Scrivere i test; rossi (funzioni inesistenti).
  3. `google_oauth.py`: le quattro funzioni e `_raise_for_google_error`, su
     `request_external`; log `google.token_error` con il solo codice.
  4. Controlli bloccanti; commit `feat(auth): chiamate a token, userinfo e revoca di Google
     (10-T08)`.

### [x] T09 – Sessione salvata e rinnovo dell'access token Google

- Criteri: 10-C19, 10-C20, 10-C21, 10-C22 (parte di libreria)
- Dipende da: T05, T08
- Test: `tests/unit/test_google_login.py::TestSessionTokenProvider`: con sessione e secret
  restituisce l'access token dopo una sola chiamata al token endpoint; sessione o secret
  assenti → `AuthenticationError` con `auth login --google`; `invalid_grant` → stesso invito e
  voce intatta; `invalid_client` → messaggio con `--replace-client-secret`; timeout e errore di
  rete → `TransportError`, una chiamata, voce intatta; risposta con `refresh_token` nuovo →
  voce aggiornata con email e data conservate; la sessione è riletta a ogni chiamata.
- Passi:
  1. Scrivere i test; rossi (modulo inesistente).
  2. `src/pynteracta/google_login.py`: lettura e scrittura della voce JSON della sessione,
     `GoogleSessionTokenProvider`, `session_token_provider(profile, profile_name, transport)`.
  3. Log `google.token_refreshed` senza email né token.
  4. Controlli bloccanti; commit `feat(auth): rinnovo dell'access token Google dalla sessione
     salvata (10-T09)`.

### [x] T10 – `InteractaClient` usa la sessione salvata

- Criteri: 10-C14, 10-C15, 10-C16, 10-C17, 10-C18, 10-C40 (sessione); exit code di 10-C19 e
  10-C21
- Dipende da: T04, T09, T20
- Test: `tests/unit/test_client.py::TestInteractaClientGoogleSession`: client dal profilo con
  sessione → token endpoint di Google (`grant_type=refresh_token`) poi scambio, browser mai
  chiamato; token in cache a 30 secondi dalla scadenza → rinnovo e richiesta con il token
  nuovo; `google_token` esplicito e variabile d'ambiente → token endpoint mai chiamato; altro
  `base_url` o altro profilo → `AuthenticationError` con l'invito; solo `base_url` →
  `open_keychain` mai chiamato; senza sessione messaggio con `auth login --google`, e con
  `keyring` assente anche `pynteracta[google]`; `InteractaClient()` con `current_profile =
  "prod"` usa la sessione di `prod`; `close()` chiude il transport di Google.
  `tests/unit/test_cli_auth.py::TestGoogleSessionCommands`: `auth whoami` con sessione e senza
  variabile d'ambiente riesce; senza sessione exit `3`; `invalid_grant` exit `3`; errore di
  rete verso Google exit `7`. Il test esistente
  `test_google_auth_method_without_token_raises` si riscrive con 10-C18.
- Passi:
  1. Scrivere i test; rossi (il client solleva sempre l'errore di oggi).
  2. `client.py::_build_token_manager`: ramo `google_oauth2` senza token e con profilo →
     `session_token_provider` su un transport dedicato; `ConfigurationError` →
     `AuthenticationError` con invito ed extra.
  3. `auth.py`: docstring di `GoogleOAuth2Credentials` (scope `email`, login integrato).
  4. Controlli bloccanti; commit `feat(auth): il client usa la sessione Google salvata
     (10-T10)`.

### [x] T11 – `google_login.login()`

- Criteri: 10-C03, 10-C04, 10-C09, 10-C11, 10-C23, 10-C30, 10-C31, 10-C32 (parte di libreria)
- Dipende da: T03, T09, T10, T20
- Test: `tests/unit/test_google_login.py::TestLogin`: login completo con `client_secret` come
  parametro → `GoogleLoginResult`, voce della sessione (refresh token, email, `login_at`), voce
  del secret, profilo con `auth_method`, connessione e `google_client_id`, `capsys` vuoto,
  `on_auth_url` chiamata quando il browser fallisce o è disattivato; senza id del client, senza
  secret → `ConfigurationError` prima di qualunque chiamata; consenso negato, timeout, risposta
  senza refresh token, scambio Interacta `401` (messaggio `not linked to an Interacta user`,
  senza email) → `config.toml` e portachiavi identici a prima; secret già salvato `A` e
  parametro `B` → il token endpoint riceve `B`, la voce diventa `B` solo a login riuscito;
  secondo profilo con lo stesso client → login senza parametro; token Interacta in cache
  eliminato a login riuscito; userinfo senza email → sessione salvata con `email: null`;
  scrittura del profilo che fallisce → voci del portachiavi riportate al valore precedente.
- Passi:
  1. Scrivere i test; rossi (funzione inesistente).
  2. `auth.py`: `clear_cached_token(profile, profile_name, api_base)`, estratta da
     `cli/auth.py::logout` con l'eliminazione della chiave vecchia di T20, che passa a usarla
     (i test di T01 e T20 restano verdi).
  3. `google_login.py`: `GoogleLoginResult` e `login()` nell'ordine del piano, con scritture
     solo dopo `users.me()` e ripristino in caso di errore.
  4. Log `google.login_ok` con la sola chiave della sessione.
  5. Controlli bloccanti; commit `feat(auth): login Google dal browser in libreria (10-T11)`.

### [x] T12 – `google_login.status()` e `logout()`

- Criteri: 10-C24, 10-C25, 10-C27, 10-C28, 10-C29, 10-C32 (parte di libreria)
- Dipende da: T11
- Test: `tests/unit/test_google_login.py::TestStatus`: campi con e senza sessione, profilo
  service account, `keyring` assente e backend rifiutato (voci non leggibili con il motivo),
  nessuna chiamata `respx`, nessun segreto in `repr`; `::TestLogout`: elimina sessione e cache
  del profilo, lascia secret e sessioni degli altri profili, nessuna chiamata di rete;
  `forget_client_secret` elimina la voce del client; `revoke` chiama l'endpoint con il refresh
  token e poi elimina; revoca fallita → voce eliminata e `TransportError` rilanciato; senza
  portachiavi elimina solo la cache e lo riporta nel risultato.
- Passi:
  1. Scrivere i test; rossi (funzioni inesistenti).
  2. `google_login.py`: `GoogleSessionStatus` e `status()`.
  3. `google_login.py`: `GoogleLogoutResult` e `logout()`, con eliminazione in `finally`; log
     `google.session_removed`.
  4. Controlli bloccanti; commit `feat(auth): stato e logout della sessione Google in libreria
     (10-T12)`.

### [x] T13 – `auth login --google` dal browser

- Criteri: 10-C01, 10-C02, 10-C03, 10-C04, 10-C05, 10-C06, 10-C07, 10-C08, 10-C09, 10-C11,
  10-C12, 10-C13, 10-C23, 10-C30, 10-C31, 10-C39 (login integrato)
- Dipende da: T04, T11
- Test: `tests/unit/test_cli_auth.py::TestAuthLoginGoogleBrowser`, uno o più test per criterio
  come nella "Strategia di test" del piano; in particolare: nessun parametro di `login` accetta
  il secret come valore (10-C07); ogni flag integrato con `--google-token` e con la variabile
  d'ambiente → exit `2` (10-C13); browser e `open_keychain` mai chiamati con il token statico
  (10-C12); `current_profile = "prod"` senza `--profile` → sessione e profilo di `prod`
  (10-C39). `tests/unit/test_cli_write.py`: `read_secret` con e senza conferma. Il test
  esistente `test_login_google_missing_token` si riscrive con 10-C04.
- Passi:
  1. Scrivere i test; rossi (flag inesistenti; senza token oggi exit `2`).
  2. `cli/_write.py`: `read_secret`, e `read_password` che la usa.
  3. `cli/auth.py::login`: flag `--google-client-id`, `--client-secret-stdin`,
     `--replace-client-secret`, `--no-browser`, `--login-timeout`; errore d'uso con un token
     statico; ramo statico invariato.
  4. `cli/auth.py::_login_google_browser`: lettura del secret quando serve (exit `2` senza
     terminale e senza flag), chiamata a `google_login.login` con `on_auth_url` che stampa
     l'indirizzo, messaggi di esito, `handle_error` per gli errori.
  5. Controlli bloccanti; commit `feat(cli): auth login --google dal browser (10-T13)`.

### [x] T14 – `auth status`

- Criteri: 10-C24, 10-C25, 10-C26
- Dipende da: T12
- Test: `tests/unit/test_cli_auth.py::TestAuthStatus`: snapshot della tabella e di `--output
  json` con sessione; exit `0` senza sessione; profilo service account, `keyring` assente e
  backend rifiutato → exit `0` con il motivo; nessuna chiamata `respx` senza `--check`;
  sentinelle di refresh token e secret assenti dall'output; `--fields` ed `--export` in
  `tmp_path`; `--check` con sessione valida → `authenticated_as` ed exit `0`, con
  `invalid_grant` → exit `3`.
- Passi:
  1. Scrivere i test; rossi (comando inesistente).
  2. `cli/auth.py::status`: `google_login.status` reso con `render_output` a record singolo.
  3. `--check`: `build_client(state).users.me()`, righe `check` e `authenticated_as`,
     `handle_error` se fallisce.
  4. Generare e leggere gli snapshot; controlli bloccanti; commit `feat(cli): auth status
     (10-T14)`.

### [x] T15 – `auth logout` con sessione Google

- Criteri: 10-C27, 10-C28, 10-C29
- Dipende da: T12
- Test: `tests/unit/test_cli_auth.py::TestAuthLogoutGoogle`: due profili con sessione, logout
  del primo → sua voce e sua cache eliminate, secret e voce del secondo presenti, nessuna
  chiamata `respx`; `--forget-client-secret` elimina la voce del client; `--revoke` chiama la
  rotta di revoca e poi elimina; revoca con errore di rete → voce eliminata, exit `7`; profilo
  `google_oauth2` con `keyring` assente → cache eliminata e nota sul portachiavi; profilo
  service account → output di oggi. I test di logout di T01 restano verdi.
- Passi:
  1. Scrivere i test; rossi (flag inesistenti, sessione non eliminata).
  2. `cli/auth.py::logout`: flag `--forget-client-secret` e `--revoke`, chiamata a
     `google_login.logout`, messaggi come nel piano.
  3. Controlli bloccanti; commit `feat(cli): auth logout elimina la sessione Google (10-T15)`.

### [x] T16 – Test sui segreti e sui dati personali lungo tutto il flusso

- Criteri: 10-C33, 10-C34, 10-C35
- Dipende da: T13, T14, T15
- Test: `tests/unit/test_google_login.py::TestNoSecretsLeak`: con
  `setup_default_logging(audit=True, audit_bodies=True, audit_raw=True)` su file in `tmp_path`,
  un hook che registra tutto e sentinelle per refresh token, authorization code, verificatore
  PKCE, id token, client secret e access token Google, si eseguono login, rinnovo, revoca e i
  loro errori (`invalid_grant`, `invalid_client`, `500` con le sentinelle nel corpo); nessuna
  sentinella nel file di audit, nei log catturati, negli oggetti passati agli hook, né in
  `str`, `repr` e `response_body` delle eccezioni; gli URL di token, userinfo e revoca
  compaiono nell'audit con metodo e stato; l'email sentinella è assente dai log e dai messaggi
  di eccezione in login, rinnovo, stato e logout.
- Passi:
  1. Scrivere i test. Se sono verdi subito, è l'esito atteso: il codice dei task precedenti
     rispetta già il vincolo.
  2. Prova di fallimento, una protezione alla volta: passare il form a `_emit_request`;
     catturare il corpo in `_emit_response`; mettere il corpo intero in `response_body`
     dell'errore di Google; aggiungere l'email a un evento di log. Per ciascuna verificare che
     almeno un test diventi rosso, poi ripristinare. Annotare l'esito nel messaggio di commit.
  3. Se una prova non fa fallire nulla, il test non dimostra il criterio: correggerlo prima di
     proseguire.
  4. Controlli bloccanti; commit `test: i segreti del login Google non compaiono in log, audit
     e hook (10-T16)`.

### [x] T17 – Documentazione pubblica

- Criteri: 10-C38
- Dipende da: T13, T14, T15
- Test: `tests/unit/test_docs_snippets.py::test_google_login_pages`: `authentication.md` non
  contiene `does **not** run any Google sign-in` e cita `auth login --google`,
  `pynteracta[google]` e `auth status`; `cli.md` cita i cinque flag del login, `auth status
  --check`, `--forget-client-secret` e `--revoke`; `configuration.md` cita `google_client_id` e
  `PYNTERACTA_GOOGLE_CLIENT_ID`. `uv run mkdocs build --strict` verde.
- Passi:
  1. Scrivere il test; rosso.
  2. `docs/authentication.md`: sezione Google riscritta (login dal browser, client "Desktop" in
     un'app "Internal", sessione e rinnovo, logout e revoca con l'avvertenza sulle altre
     sessioni, portachiavi supportati, token statico come alternativa).
  3. `docs/configuration.md`, `docs/cli.md` (compreso il profilo corrente come predefinito di
     `auth login`), `docs/api/google_login.md` e voce in `mkdocs.yml`.
  4. `docs/index.md` e `README.md`: login dal browser ed extra `google`, senza numeri di
     versione.
  5. `uv run mkdocs build --strict`; controlli bloccanti; commit `docs: login Google dal
     browser (10-T17)`.

### [x] T21 – Id e secret del client dal file JSON della console

- Criteri: 10-C42, 10-C43, 10-C44, 10-C45
- Dipende da: T13, T17
- Test: `test_google_oauth.py::TestReadClientFile`, `test_google_login.py::TestLoginClientFile`,
  `test_cli_auth.py::TestAuthLoginClientFile`; in `test_docs_snippets.py::test_google_login_pages`
  `cli.md` e `authentication.md` citano `--google-client-file`.
- Passi:
  1. Scrivere i test; rossi. Per 10-C43 provare che il test di non divulgazione fallisce
     riportando il contenuto del file nel messaggio d'errore, poi togliere la regressione.
  2. `google_oauth.read_client_file` e `OAuthClient`.
  3. `google_login.login(client_file=…)`: lettura prima di ogni richiesta, controlli dei
     conflitti, secret del file come valore nuovo.
  4. `cli/auth.py`: opzione `--google-client-file`, tra i flag del login integrato; conflitto
     con `--client-secret-stdin`.
  5. `docs/cli.md`, `docs/authentication.md` (il file si scarica dalla console e va cancellato
     dopo il login).
  6. Controlli bloccanti e `mkdocs build --strict`; commit `feat(cli): id e secret del client
     Google dal file JSON della console (10-T21)`.

### [ ] T22 – Nota di `auth logout` quando non c'è nulla da revocare o eliminare

- Criteri: 10-C46
- Dipende da: T15
- Test: `test_cli_auth.py::TestAuthLogoutNothingToDo`.
- Passi:
  1. Scrivere i test; rossi.
  2. `cli/auth.py::logout`: note per `--revoke` senza sessione e `--forget-client-secret` senza
     secret, sui profili `google_oauth2` e con service account.
  3. `docs/cli.md`: una riga sulla nota.
  4. Controlli bloccanti e `mkdocs build --strict`; commit `feat(cli): auth logout segnala
     quando non c'è nulla da revocare (10-T22)`.

### [ ] T18 – Prova reale su macOS e Windows (manuale)

- Criteri: sezione "Verifica manuale" della spec (10-C03, 10-C14, 10-C15, 10-C29 sui sistemi
  reali)
- Chi: maintainer
- Cosa fare: con il client "Desktop" dell'ente, su una postazione macOS e una Windows con
  `pynteracta[google]` installato dal branch:
  1. `pynteracta auth login --google --google-client-id <id>` contro il tenant: consenso nel
     browser, identità mostrata, voce `pynteracta` presente nel Portachiavi o nella Gestione
     credenziali.
  2. `pynteracta auth status` e `pynteracta auth whoami` senza variabili d'ambiente.
  3. Dopo più di un'ora, di nuovo `auth whoami`: deve riuscire senza browser.
  4. `pynteracta auth logout --revoke`, poi `auth whoami`: deve chiedere di rifare il login
     (exit `3`).
  5. Su una delle due postazioni, un nuovo login con `--google-client-file` sul JSON scaricato
     dalla console (dopo T21).
  Riportare qui gli esiti, senza token né segreti.
- Esito: <compilato a mano>

### [ ] T19 – Chiusura: `CLAUDE.md` e PRD

- Criteri: nessuno (documenti di governo; i "Requisiti nuovi" della spec)
- Dipende da: T17, T18, T21, T22
- Test: nessuno; si verifica rileggendo il diff e con `uv run pre-commit run --all-files`.
- Passi:
  1. `CLAUDE.md`: mappa dei moduli (`keychain.py`, `google_oauth.py`, `google_login.py`,
     `request_external` in `transport.py`), "Stack" (`keyring` opzionale, extra `google`),
     introduzione (il login Google non è più "da realizzare").
  2. `specs/prd.md`: RF-026a…g, RF-016a, RF-016b, RNF-012a, RNF-001c dal provvisorio al
     definitivo; RF-026, RNF-012 e RNF-001 non più "da realizzare"; §6 con l'email dell'account
     tra i dati nel portachiavi; date di conferma di §2, §5, §6, §7; riga nella storia del
     documento.
  3. `specs/10-google-login/spec.md`: esiti di T18 nella sezione "Verifica manuale".
  4. Controlli bloccanti e `uv run pre-commit run --all-files`; commit `docs: chiusura della
     spec 10, PRD e CLAUDE.md (10-T19)`.

## Copertura dei criteri

| Criterio | Task |
|---|---|
| 10-C01 | T07, T13 |
| 10-C02 | T13 |
| 10-C03 | T11, T13, T18 |
| 10-C04 | T02, T11, T13 |
| 10-C05 | T05, T13 |
| 10-C06 | T05, T13 |
| 10-C07 | T13 |
| 10-C08 | T07, T13 |
| 10-C09 | T11, T13 |
| 10-C10 | T07 |
| 10-C11 | T11, T13 |
| 10-C12 | T01, T13 |
| 10-C13 | T13 |
| 10-C14 | T10, T18 |
| 10-C15 | T10, T18 |
| 10-C16 | T01, T10 |
| 10-C17 | T10 |
| 10-C18 | T10 |
| 10-C19 | T09, T10 |
| 10-C20 | T08, T09 |
| 10-C21 | T08, T09, T10 |
| 10-C22 | T09 |
| 10-C23 | T11, T13 |
| 10-C24 | T12, T14 |
| 10-C25 | T12, T14 |
| 10-C26 | T14 |
| 10-C27 | T12, T15 |
| 10-C28 | T12, T15 |
| 10-C29 | T12, T15, T18 |
| 10-C30 | T11, T13 |
| 10-C31 | T11, T13 |
| 10-C32 | T11, T12 |
| 10-C33 | T16 |
| 10-C34 | T06, T16 |
| 10-C35 | T16 |
| 10-C36 | T07 |
| 10-C37 | T05 |
| 10-C38 | T17 |
| 10-C39 | T04, T13 |
| 10-C40 | T04, T10 |
| 10-C41 | T20 |
| 10-C42 | T21 |
| 10-C43 | T21 |
| 10-C44 | T21 |
| 10-C45 | T21 |
| 10-C46 | T22 |
