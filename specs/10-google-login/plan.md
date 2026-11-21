# Piano 10 – Login Google integrato con rinnovo automatico

Stato: approvato
Spec: [spec.md](spec.md)

## Panoramica

Tre moduli nuovi e modifiche piccole a quelli esistenti. `keychain.py` incapsula `keyring`
(importato solo lì, in modo pigro) e decide quali portachiavi sono accettati. `google_oauth.py`
contiene il protocollo: PKCE, indirizzo di consenso, listener su loopback, chiamate a token,
userinfo e revoca, mappatura degli errori di Google. `google_login.py` è la superficie
pubblica: `login()`, `logout()`, `status()` e il provider che rinnova l'access token Google
dalla sessione salvata. Il rinnovo non tocca la gestione dei token: il provider si passa al
`GoogleOAuth2TokenManager` esistente come `token_provider`, quindi cache, anticipo di 60 secondi
e scambio con Interacta restano quelli di oggi. Le chiamate a Google passano da un metodo nuovo
di `HttpTransport`, `request_external`, costruito come `post_multipart` della spec 04: stesso
percorso di log, audit e hook, corpo sempre assente. `InteractaClient` cerca la sessione solo
quando il profilo è `google_oauth2` e non c'è né token né provider. La CLI aggiunge i flag di
`auth login`, il comando `auth status` e i flag di `auth logout`, e delega tutto alla libreria;
le funzioni che scrivono un profilo in `config.toml` passano da `cli/auth.py` a `config.py`,
perché le usa anche `login()`. Test prima del codice; i test di caratterizzazione fissano il
login statico, il logout e la precedenza dei token prima di toccarli.

## Moduli e file

| File | Nuovo o modificato | Responsabilità |
|---|---|---|
| `src/pynteracta/exceptions.py` | modificato | `ConfigurationError(InteractaError)`: id del client mancante, extra non installato, portachiavi non disponibile, client secret non fornito |
| `src/pynteracta/config.py` | modificato | `Profile.google_client_id: str \| None` e lo stesso campo in `_EnvSettings` (`PYNTERACTA_GOOGLE_CLIENT_ID`); `config_file_path(config_file) -> Path`; `resolve_profile_name(profile_name, config_file) -> str` (nome dato, altrimenti `current_profile`); `write_profile_fields(config_path, name, *, connection: Profile, fields: Mapping[str, str])`, che riunisce `_load_config_doc`, `_profile_table` e `_persist_connection` oggi in `cli/auth.py` (con `tomlkit`, commenti conservati) |
| `src/pynteracta/keychain.py` | nuovo | `open_keychain() -> Keychain`: importa `keyring` (assente → `ConfigurationError` che cita `pynteracta[google]`), controlla il backend contro l'elenco degli accettati (assente, nullo o su file → `ConfigurationError` che rimanda al token statico). `Keychain.get/set/delete(entry)` sul servizio `pynteracta`; `session_entry(api_base, profile_name)` e `client_secret_entry(client_id)` costruiscono i nomi delle voci. Gli errori di `keyring` diventano `ConfigurationError` senza il valore |
| `src/pynteracta/google_oauth.py` | nuovo | costanti degli endpoint (`AUTH_URL`, `TOKEN_URL`, `USERINFO_URL`, `REVOKE_URL`) e dello scope; `new_pkce()`, `build_auth_url(...)`; `LoopbackReceiver` (listener); `exchange_code(...)`, `refresh_access_token(...)`, `fetch_email(...)`, `revoke(...)` su `HttpTransport.request_external`; `_raise_for_google_error(response)` |
| `src/pynteracta/google_login.py` | nuovo | superficie pubblica: `login()`, `logout()`, `status()`, i risultati `GoogleLoginResult` e `GoogleSessionStatus` (dataclass congelate), `GoogleSessionTokenProvider` (callable per `token_provider`) e `session_token_provider(profile, profile_name, transport)` usato dal client |
| `src/pynteracta/transport.py` | modificato | `request_external(method, url, *, form=None, bearer_token=None) -> httpx.Response`: URL assoluto, solo `User-Agent` e, se dato, `Authorization: Bearer`; `_emit_request` ed `_emit_response` con corpo `None` e `capture_body=False`; restituisce la risposta con qualunque stato (la mappa il chiamante); timeout e rete → `TransportError` da `_send`. `notify_error(err)`: passa un errore a `hooks.on_error` |
| `src/pynteracta/auth.py` | modificato | docstring di `GoogleOAuth2Credentials` (scope `email`, login integrato); `clear_cached_token(profile, profile_name, api_base)`, estratta da `auth logout`, usata dal logout e da `login()` |
| `src/pynteracta/client.py` | modificato | nome effettivo del profilo con `resolve_profile_name` quando il client risolve da sé il profilo; in `_build_token_manager`, ramo `google_oauth2` senza token: `session_token_provider(...)` su un transport dedicato agli endpoint di Google, chiuso da `close()`; `ConfigurationError` del portachiavi → `AuthenticationError` con l'invito al login e il nome dell'extra |
| `src/pynteracta/cli/_common.py` | modificato | `ConfigurationError: EXIT_CONFIG` in `_EXIT_MAP`; `config_path_from_state` delega a `config.config_file_path` |
| `src/pynteracta/cli/_write.py` | modificato | `read_secret(*, prompt, option, confirm)`, di cui `read_password` diventa un caso (`prompt="Password"`, `confirm=True`) |
| `src/pynteracta/cli/auth.py` | modificato | `login`: flag nuovi, profilo corrente come predefinito, ramo integrato; `status` (nuovo); `logout`: sessione Google, `--forget-client-secret`, `--revoke` |
| `pyproject.toml`, `uv.lock` | modificati | extra `google = ["keyring>=25"]`; `keyring` nel gruppo `dev`, perché unit test e mypy lo importano |
| `tests/unit/google_fakes.py` | nuovo | `MemoryKeychain` (stessa interfaccia di `Keychain`), `FakeBrowser` (segue il redirect con `urllib` in un thread, con codice e `state` scelti dal test), risposte di Google per `respx`, valori sentinella dei segreti |
| `tests/unit/conftest.py` | modificato | fixture `memory_keychain`, che sostituisce `keychain.open_keychain` |
| `tests/unit/test_keychain.py` | nuovo | backend accettati e rifiutati, extra assente, nomi delle voci |
| `tests/unit/test_google_oauth.py` | nuovo | PKCE, indirizzo di consenso, listener, chiamate ed errori di Google |
| `tests/unit/test_google_login.py` | nuovo | `login()`, `logout()`, `status()`, provider di sessione, test sui segreti |
| `tests/unit/test_transport.py`, `test_exceptions.py`, `test_config.py`, `test_client.py`, `test_auth.py`, `test_cli_auth.py`, `test_cli_common.py`, `test_cli_write.py` | modificati | criteri e test di caratterizzazione delle parti toccate |
| `tests/unit/test_docs_snippets.py` | modificato | `test_google_login_pages` (10-C38) |
| `docs/authentication.md` | modificato | sezione "Google OAuth2" riscritta: login dal browser, creazione del client "Desktop" in un'app "Internal", sessione e rinnovo, logout e revoca, portachiavi supportati, token statico come alternativa |
| `docs/configuration.md`, `docs/cli.md` | modificati | campo e variabile `google_client_id`; `auth login` (flag nuovi, profilo corrente), `auth status`, `auth logout` |
| `docs/api/google_login.md`, `mkdocs.yml` | nuovo, modificato | riferimento di `pynteracta.google_login` con `mkdocstrings` e voce di navigazione |
| `docs/index.md`, `README.md` | modificati | l'autenticazione Google comprende il login dal browser; installazione con l'extra `google`; nessun numero di versione |
| `CLAUDE.md` | modificato | mappa dei moduli (`keychain.py`, `google_oauth.py`, `google_login.py`) e "Stack" (`keyring` opzionale) |
| `specs/prd.md` | modificato (task di chiusura) | RF-026a…g, RF-016a, RF-016b, RNF-012a, RNF-001c dal provvisorio al definitivo; §6 con l'email dell'account; storia del documento |

## Modello dati e migrazioni

Nessun database. Dati nuovi:

- **Profilo** (`config.toml`): `google_client_id`, stringa facoltativa. I profili esistenti
  restano validi.
- **Portachiavi**, servizio `pynteracta`:
  - voce `google-session:<chiave>`, dove `<chiave>` è `build_cache_key(api_base, profilo)`, la
    stessa della cache del token: JSON `{"refresh_token": …, "email": … | null, "login_at":
    <ISO 8601 UTC>}`;
  - voce `google-client-secret:<client_id>`: il client secret, come stringa.

Nessuna migrazione: chi usa il token statico non ha voci nel portachiavi. Il cambio del nome
predefinito del profilo (10-C39, 10-C40) non sposta dati: chi ha `current_profile` diverso da
`default` e un token in cache sotto `default` ottiene un token nuovo alla prima chiamata.

## Flussi

Login (`google_login.login`, chiamata da `auth login --google`):

```
resolve_profile + resolve_profile_name
client_id = parametro o profilo             → assente: ConfigurationError
open_keychain()                             → extra o backend: ConfigurationError
secret = parametro o voce del client        → assente: ConfigurationError
verifier, challenge, state = new_pkce()
receiver = LoopbackReceiver()               bind 127.0.0.1, porta libera
url = build_auth_url(client_id, redirect, challenge, state)   scope=email, access_type=offline, prompt=consent
open_browser(url)                           fallisce o disattivato: on_auth_url(url)
code = receiver.wait(state, timeout)        state diverso, error=…, timeout: AuthenticationError
tokens = exchange_code(code, verifier, secret)   invalid_client: AuthenticationError; senza refresh_token: AuthenticationError
email = fetch_email(tokens.access_token)    GET userinfo; email assente: None
InteractaClient(profilo in memoria, google_token=tokens.access_token).users.me()
                                            401: AuthenticationError "not linked to an Interacta user"
--- solo da qui si scrive ---
keychain.set(sessione); keychain.set(secret) se nuovo o diverso
write_profile_fields(auth_method, connessione, google_client_id)
clear_cached_token(profilo)
→ GoogleLoginResult(profile_name, base_url, email, user_name)
```

Se la scrittura del profilo fallisce dopo quella del portachiavi, le voci appena scritte sono
riportate al valore precedente prima di rilanciare l'errore. Il listener è chiuso in un blocco
`finally`, anche su `KeyboardInterrupt`.

Listener: `http.server.HTTPServer` su `("127.0.0.1", 0)`, un `handle_request()` alla volta con
scadenza. Una richiesta senza `code` né `error` nella query (per esempio `/favicon.ico`) riceve
`404` e non conta; la prima che li ha riceve la pagina di esito (`text/plain`) e chiude il
socket. `log_message` è sovrascritto e non scrive nulla: la riga di richiesta contiene il
codice.

Rinnovo (`GoogleSessionTokenProvider.__call__`, invocato dal `GoogleOAuth2TokenManager` quando
il token Interacta manca o scade):

```
sessione = keychain.get(voce della sessione)   → assente: AuthenticationError (invito al login)
secret   = keychain.get(voce del client)       → assente: AuthenticationError (invito al login)
risposta = refresh_access_token(refresh_token, client_id, secret)
   invalid_grant  → AuthenticationError "run `pynteracta auth login --google`"
   invalid_client → AuthenticationError "… --replace-client-secret"
   timeout, rete  → TransportError (da _send, una richiesta)
   5xx            → ServerError
se la risposta ha un refresh_token diverso → keychain.set(sessione aggiornata)
→ access_token Google → scambio con Interacta (codice esistente)
```

Il client controlla alla costruzione che la sessione esista, così l'errore arriva subito come
oggi (10-C18); refresh token e secret sono riletti a ogni rinnovo.

Logout (`google_login.logout`): `clear_cached_token`; con `revoke`, `revoke(refresh_token)`
prima dell'eliminazione, che avviene comunque in un `finally`, poi l'errore della revoca è
rilanciato; con `forget_client_secret`, elimina la voce del client. Senza portachiavi elimina
solo la cache e lo riporta nel risultato.

Stato (`google_login.status`): legge profilo e portachiavi, nessuna rete; `auth status --check`
aggiunge `build_client(state).users.me()`.

## Interfaccia

CLI, testi in inglese (deroga del `CLAUDE.md`).

- `auth login`: `--google-client-id ID`, `--client-secret-stdin`, `--replace-client-secret`,
  `--no-browser`, `--login-timeout SECONDS` (predefinito 300). Il secret si legge con
  `read_secret(prompt="Google OAuth client secret", option="--client-secret-stdin",
  confirm=False)` quando manca nel portachiavi o è richiesta la sostituzione; senza terminale e
  senza `--client-secret-stdin` exit `2` con `Client secret required: run interactively or pass
  --client-secret-stdin.` L'indirizzo di consenso è stampato con `Open this URL to sign in:`.
  Esito: `✓ Authenticated as: <nome>` e `✓ Google session saved for profile '<nome>'`.
- Errori d'uso (exit `2`): flag del login integrato insieme a `--google-token` o alla variabile
  d'ambiente (`… cannot be combined with a static Google token; unset
  $PYNTERACTA_GOOGLE_OAUTH2_TOKEN to sign in from the browser.`); `google_client_id` mancante
  (`No OAuth client configured: set google_client_id in the profile or pass
  --google-client-id.`); extra mancante (`… install pynteracta[google]`); portachiavi assente
  (`No system keychain available: use a static Google token instead …`).
- `auth status [--check]`: righe `profile`, `base_url`, `auth_method`, `google_client_id`,
  `keychain`, `google_session`, `google_account`, `google_login_at`, `client_secret_saved`; con
  `--check` anche `check` e `authenticated_as`. Passa da `render_output` (comando a record
  singolo, come `auth whoami`), quindi `--output`, `--full`, `--fields` ed `--export` compongono.
- `auth logout [--forget-client-secret] [--revoke]`: alla riga di oggi aggiunge `✓ Google
  session removed for profile '<nome>'.`, `✓ Client secret removed.`, `✓ Google session
  revoked.`, o la nota che il portachiavi non è leggibile.
- Pagina dopo il redirect: `Sign-in complete. You can close this window.` oppure `Sign-in
  failed. Return to the terminal for details.`; testo semplice, leggibile da uno screen reader,
  senza script né dati della richiesta.

Libreria (`pynteracta.google_login`):

```python
login(profile_name=None, *, config_file=None, overrides=None, client_id=None,
      client_secret=None, replace_client_secret=False, open_browser=True, timeout=300.0,
      on_auth_url=None, hooks=None) -> GoogleLoginResult
logout(profile_name=None, *, config_file=None, overrides=None,
       forget_client_secret=False, revoke=False) -> GoogleLogoutResult
status(profile_name=None, *, config_file=None, overrides=None) -> GoogleSessionStatus
```

`overrides` è lo stesso dizionario di `resolve_profile` (la CLI vi passa i flag globali).
Nessuna funzione scrive sullo standard output: l'indirizzo di consenso arriva a `on_auth_url`.

## Configurazione

- `google_client_id` nel profilo, `PYNTERACTA_GOOGLE_CLIENT_ID` in ambiente, nessun valore
  predefinito; documentato in `docs/configuration.md`. Si imposta anche con
  `config set google_client_id …`, che accetta già qualunque chiave.
- Nessuna variabile nuova in `tests/integration/.env.example`: i test di integrazione non
  usano il login integrato.
- Gli endpoint di Google sono costanti di modulo, non configurabili.

## Sicurezza e dati personali

- **Token e segreti mai nei log.** Le chiamate a Google passano solo da `request_external`,
  che non riceve mai un corpo da registrare: `audit_log_bodies` e `audit_log_raw` non hanno
  nulla da mostrare. L'header `Authorization` della chiamata a userinfo è redatto da
  `redact_headers`, come oggi. Le eccezioni nate da una risposta di Google portano in
  `response_body` solo `error` ed `error_description`, mai il corpo intero. I log applicativi
  nuovi (`google.login_ok`, `google.token_refreshed`, `google.session_removed`,
  `google.token_error`) hanno come campi solo il codice d'errore di Google e la chiave della
  sessione. Il listener non registra le richieste. Nessun `repr` dei risultati contiene
  segreti: `GoogleLoginResult` e `GoogleSessionStatus` non li hanno tra i campi.
- **Segreti di lunga durata solo nel portachiavi.** `keychain.py` è l'unico punto che legge e
  scrive refresh token e client secret; rifiuta i backend fuori dall'elenco (`macOS`,
  `Windows`, `SecretService`, `libsecret`, `kwallet`, e un `ChainerBackend` solo se tutti i suoi
  backend sono nell'elenco) e non ha ripiego. Il secret entra da prompt nascosto, stdin o
  parametro di funzione, mai da un'opzione con valore.
- **Segreti fuori dal repository.** Negli esempi e nei test: `000000000000-example.apps.
  googleusercontent.com`, `GOCSPX-example-not-a-secret`, `1//example-refresh-token`.
- **Dati personali fuori dai log.** L'email sta nel portachiavi e nell'output di `auth status`;
  non è mai un campo di log né parte di un messaggio di eccezione (il messaggio "account non
  collegato" non la cita).
- **Nessuna operazione ripetuta.** Una richiesta sola per token, userinfo e revoca; nessun
  nuovo tentativo, nemmeno sul rinnovo.
- **Soglie.** Copertura dei file nuovi e toccati ≥ 85 %; nessuna regola di ruff o mypy
  allentata (`keyring` ha i tipi).
- **Listener.** Solo `127.0.0.1`, porta scelta dal sistema, `state` confrontato con
  `secrets.compare_digest`, una sola risposta, scadenza.

## Test di caratterizzazione

Scritti e verdi prima di modificare il codice che descrivono.

| Codice esistente | Comportamento da fissare | Test previsto |
|---|---|---|
| `cli/auth.py::_login_google` | con token statico e scambio rifiutato (`401`), il profilo è già stato scritto con `auth_method` e connessione, exit `3` | `test_cli_auth.py::TestAuthLoginGoogle::test_static_login_writes_profile_before_validation` |
| `cli/auth.py::login` | senza `--profile` e con `current_profile` assente o `default`, il login (statico e service account) scrive in `default` | `test_cli_auth.py::TestAuthLoginGoogle::test_static_login_without_profile_uses_default_when_current_is_default` |
| `cli/auth.py::logout` | profilo non risolvibile → exit `1`; profilo `google_oauth2` → elimina la voce di cache con chiave tenant + nome del profilo | `test_cli_auth.py::TestAuthLogout::test_logout_unresolvable_profile_exits_1`, `::test_logout_google_profile_clears_profile_key` |
| `client.py::_build_token_manager` | `google_token` esplicito vince su `profile.google_oauth2_token` (variabile d'ambiente); `google_token_provider` esplicito con token nel profilo solleva l'errore di `GoogleOAuth2Credentials` | `test_client.py::TestInteractaClientGoogleOAuth2::test_explicit_token_wins_over_profile_token`, `::test_explicit_provider_with_profile_token` |
| `cli/_write.py::read_password` | prompt nascosto con conferma da terminale; prima riga di stdin altrimenti; stringa vuota → exit `2` | già coperto in `test_cli_write.py`; si verifica prima di estrarre `read_secret`, senza test nuovi |
| `transport.py::post_multipart` | corpo assente in audit e hook | già coperto in `test_transport.py` (spec 04); nessun test nuovo |

I test esistenti `test_login_google_missing_token` (oggi exit `2`) e
`test_google_auth_method_without_token_raises` descrivono comportamenti che la spec cambia: si
riscrivono con i criteri 10-C04 e 10-C18.

## Strategia di test

Tutti i test sono unitari, senza rete: `respx` simula gli endpoint di Google e di Interacta,
`FakeBrowser` segue il redirect verso il listener reale su loopback, `MemoryKeychain`
sostituisce il portachiavi. Ogni test porta il marker `# criterio: 10-C<mm>`. Per i test sui
segreti (10-C33, 10-C34, 10-C36) il task prevede la prova che falliscano: si passa
temporaneamente il corpo a `_emit_request` e `_emit_response`, e si ripristina il
`log_message` predefinito del listener, e si verifica che i test diventino rossi.

| Criterio | Test previsto | Tipo |
|---|---|---|
| 10-C01 | `test_google_oauth.py`: `build_auth_url` contiene id del client, `scope=email` e nessun altro scope, `code_challenge_method=S256`, challenge coerente con il verificatore, `state`, redirect `http://127.0.0.1:<porta>`; `test_cli_auth.py`: l'indirizzo passato al browser finto ha gli stessi parametri | unitario |
| 10-C02 | `test_cli_auth.py`: browser che restituisce `False` → indirizzo nell'output; `--no-browser` → browser finto mai chiamato e indirizzo nell'output | unitario |
| 10-C03 | `test_cli_auth.py`: login completo → output, exit `0`, profilo con `auth_method`, `base_url`, `google_client_id`; voce della sessione con refresh token, email, `login_at` | unitario |
| 10-C04 | `test_cli_auth.py`: senza id del client → exit `2`, messaggio con `google_client_id`, nessuna chiamata `respx`, browser mai chiamato; `test_google_login.py`: `login()` solleva `ConfigurationError` | unitario |
| 10-C05 | `test_keychain.py`: con `sys.modules["keyring"] = None`, `open_keychain` solleva `ConfigurationError` con `pynteracta[google]`; `test_cli_auth.py`: exit `2` | unitario |
| 10-C06 | `test_keychain.py`: backend `fail`, `null` e uno fuori elenco (file in chiaro) rifiutati, quelli in elenco e un chainer omogeneo accettati; `test_cli_auth.py`: exit `2`, messaggio con il token statico, `tmp_path` senza file nuovi | unitario |
| 10-C07 | `test_cli_auth.py`: prompt nascosto da terminale (senza conferma); `--client-secret-stdin` con `input=`; senza terminale e senza flag exit `2` e browser mai chiamato; nessun parametro del comando accetta il secret come valore (ispezione dei parametri di `login`) | unitario |
| 10-C08 | `test_google_oauth.py`: `LoopbackReceiver.wait` con `state` diverso solleva `AuthenticationError`; `test_cli_auth.py`: exit `3`, rotta del token mai chiamata, portachiavi e profilo invariati | unitario |
| 10-C09 | `test_cli_auth.py`, parametrizzato: `error=access_denied`, timeout (`--login-timeout` di pochi decimi), risposta senza `refresh_token` → exit `3`, `config.toml` e portachiavi identici byte per byte | unitario |
| 10-C10 | `test_google_oauth.py`: indirizzo del socket `127.0.0.1`; seconda connessione dopo la prima risposta rifiutata; socket chiuso dopo il timeout; richiesta senza `code` ignorata | unitario |
| 10-C11 | `test_cli_auth.py`: scambio Interacta `401` → exit `3`, messaggio `not linked to an Interacta user`, profilo e portachiavi invariati, secret appena inserito assente | unitario |
| 10-C12 | `test_cli_auth.py`: test statici esistenti più: browser e `open_keychain` mai chiamati con `--google-token` e con la variabile d'ambiente | unitario |
| 10-C13 | `test_cli_auth.py`, parametrizzato su ogni flag integrato con `--google-token` e con la variabile → exit `2`, nessuna chiamata | unitario |
| 10-C14 | `test_client.py`: `InteractaClient(profile_name=…)` con sessione → rotta del token Google chiamata con `grant_type=refresh_token`, poi scambio; `test_cli_auth.py`: `auth whoami` senza variabile d'ambiente; browser mai chiamato | unitario |
| 10-C15 | `test_client.py`: token in cache a 30 secondi dalla scadenza → nuova chiamata a Google e a Interacta, richiesta API con il token nuovo | unitario |
| 10-C16 | `test_client.py`: con sessione, `google_token` esplicito e poi variabile d'ambiente → rotta del token Google mai chiamata | unitario |
| 10-C17 | `test_client.py`: stesso profilo con altro `base_url`, altro profilo sullo stesso tenant → `AuthenticationError` con l'invito; `InteractaClient(base_url=…)` → `open_keychain` mai chiamato | unitario |
| 10-C18 | `test_client.py`: senza sessione → messaggio con `auth login --google`; con `keyring` assente anche `pynteracta[google]`; `test_cli_auth.py`: exit `3` | unitario |
| 10-C19 | `test_google_login.py`: rinnovo con `400 invalid_grant` → `AuthenticationError` con l'invito, voce intatta, browser mai chiamato; `test_cli_auth.py`: exit `3` | unitario |
| 10-C20 | `test_google_login.py`: `invalid_client` al rinnovo e allo scambio del codice → messaggio con `--replace-client-secret` | unitario |
| 10-C21 | `test_google_login.py`: `httpx.ConnectTimeout` e `httpx.ConnectError` sulla rotta del token → `TransportError`, una sola chiamata, voce intatta; `test_cli_auth.py`: exit `7` | unitario |
| 10-C22 | `test_google_login.py`: risposta di rinnovo con `refresh_token` nuovo → voce aggiornata, email e data conservate | unitario |
| 10-C23 | `test_cli_auth.py`: cache su file con un token valido, nuovo login → voce di cache eliminata e chiamata successiva con il token del nuovo scambio | unitario |
| 10-C24 | `test_cli_auth.py`: `auth status` tabella e `--output json` (snapshot `syrupy`), nessuna chiamata `respx`, sentinelle di refresh token e secret assenti dall'output, exit `0` senza sessione | unitario |
| 10-C25 | `test_cli_auth.py`: profilo service account; `keyring` assente; backend rifiutato → exit `0` e voci con il motivo | unitario |
| 10-C26 | `test_cli_auth.py`: `--check` con sessione valida → identità ed exit `0`; con `invalid_grant` → exit `3` | unitario |
| 10-C27 | `test_cli_auth.py`: due profili con sessione, logout del primo → sua voce e sua cache eliminate, secret e voce del secondo presenti, nessuna chiamata `respx` | unitario |
| 10-C28 | `test_cli_auth.py`: `--forget-client-secret` → voce del client eliminata | unitario |
| 10-C29 | `test_cli_auth.py`: `--revoke` → rotta di revoca chiamata con il refresh token, voce eliminata; revoca con errore di rete → voce eliminata comunque, exit `7` | unitario |
| 10-C30 | `test_cli_auth.py`: secret salvato `A`, login con `--client-secret-stdin` `B` → la rotta del token riceve `B`, la voce diventa `B`; con login fallito resta `A`; lo stesso con `--replace-client-secret` e prompt | unitario |
| 10-C31 | `test_cli_auth.py`: due profili con lo stesso id del client → al secondo login `read_secret` non è chiamata | unitario |
| 10-C32 | `test_google_login.py`: `login(client_secret=…)` con `capsys` vuoto, stessa voce e stesso profilo della CLI; `status()` e `logout()` con gli esiti di 10-C24 e 10-C27 | unitario |
| 10-C33 | `test_google_login.py`: con `setup_default_logging(audit=True, audit_bodies=True, audit_raw=True)` su file, un hook che registra tutto e sentinelle per i sei segreti, si eseguono login, rinnovo, revoca e i loro errori (`invalid_grant`, `invalid_client`, `500` con il segreto nel corpo); nessuna sentinella nel file di audit, nei log catturati, negli oggetti passati agli hook, né in `str`, `repr` e `response_body` delle eccezioni | unitario |
| 10-C34 | `test_transport.py`: `request_external` emette `audit.request`/`audit.response` e chiama gli hook con metodo, URL e stato e `body is None`, con e senza `audit_bodies`; `test_google_login.py`: gli URL di token, userinfo e revoca compaiono nell'audit | unitario |
| 10-C35 | `test_google_login.py`: email sentinella assente dai log catturati e dai messaggi di eccezione in login, rinnovo, stato e logout | unitario |
| 10-C36 | `test_google_oauth.py`: il corpo della pagina di esito, riuscita e fallita, non contiene codice, `state` né token; `capfd` vuoto (nessuna riga di richiesta sullo standard error) | unitario |
| 10-C37 | `test_keychain.py`: `tomllib` su `pyproject.toml` → `keyring` assente da `dependencies` e presente in `optional-dependencies.google`; con `sys.modules["keyring"] = None`, `import pynteracta.client`, `pynteracta.cli` e `auth whoami` con service account funzionano | unitario |
| 10-C38 | `test_docs_snippets.py::test_google_login_pages`: `authentication.md` non contiene `does **not** run any Google sign-in` e cita `auth login --google`, `pynteracta[google]`, `auth status`; `cli.md` e `configuration.md` citano flag e campo nuovi; `uv run mkdocs build --strict` tra i controlli di verifica | unitario, più controllo di verifica |
| 10-C39 | `test_cli_auth.py`, parametrizzato sui tre login: `current_profile = "prod"` senza `--profile` → scrive in `prod`, nessun profilo `default`; con `--profile X` scrive in `X` | unitario |
| 10-C40 | `test_client.py`: `current_profile = "prod"`, `InteractaClient()` → voce di sessione e chiave di cache di `prod` | unitario |
| Verifica manuale della spec | login reale su macOS e Windows contro il tenant, rinnovo dopo un'ora, `logout --revoke` | manuale |

## Scelte tecniche

| Scelta | Alternative scartate | Motivo |
|---|---|---|
| Chiamate a Google con `HttpTransport.request_external` | `httpx.Client` dedicato nel modulo Google | Una sola via per log, audit, hook e `TransportError`; la garanzia "mai il corpo" sta in un punto solo (scelta del maintainer) |
| Email dall'endpoint userinfo | Claim dell'id token; id token con ripiego su userinfo | Un solo percorso da testare, e non dipende dal fatto che Google restituisca l'id token con il solo scope `email` (scelta del maintainer) |
| Modulo pubblico `pynteracta.google_login` e nuova `ConfigurationError` | Solo eccezioni esistenti | Chi usa la libreria distingue "configura" da "rifai il login"; la CLI la mappa su exit `2` con `_EXIT_MAP` (scelta del maintainer) |
| Il rinnovo è un `token_provider` del `GoogleOAuth2TokenManager` esistente | Un terzo token manager | Cache, anticipo di 60 secondi, invalidazione e scambio sono già testati; il codice nuovo si limita a procurare l'access token Google |
| `keyring` importato solo in `keychain.py`, dentro la funzione | Import a livello di modulo con `try/except` | L'installazione base non lo vede mai; i test sostituiscono un solo punto |
| Elenco dei backend accettati, per nome del modulo | Elenco dei rifiutati; soglia sulla `priority` di `keyring` | Un backend nuovo o sconosciuto è rifiutato finché non lo si aggiunge: nessun ripiego silenzioso (RNF-012) |
| Sessione in una voce JSON unica; secret in una voce per client | Tre voci separate per refresh token, email e data | Scrittura ed eliminazione atomiche della sessione; la voce resta sotto il limite della Gestione credenziali di Windows (circa 1 280 caratteri) |
| Listener con `http.server` della libreria standard, porta scelta dal sistema | Porta fissa; libreria esterna (`google-auth-oauthlib`) | Nessuna dipendenza in più; i client "Desktop" accettano qualunque porta su loopback |
| La sessione si legge a ogni rinnovo, non alla costruzione del client | Refresh token tenuto in memoria nel client | Un processo lungo (il server MCP della spec 11) vede un nuovo login o un refresh token ruotato senza riavvio |
| L'access token Google non si mette in cache | Cache in memoria con scadenza | Serve una volta per scambio, cioè una volta all'ora; una cache sarebbe un segreto in più da custodire |
| `write_profile_fields` e `config_file_path` in `config.py` | Lasciarle in `cli/auth.py` e importarle dalla libreria | La libreria non importa dalla CLI |
| `keyring` nel gruppo `dev` | Test che simulano sempre l'assenza | mypy controlla `keychain.py` contro i tipi veri; l'assenza si simula solo nei test che la riguardano |

## Rischi

- Google non restituisce il refresh token se il consenso è già stato dato → la richiesta usa
  sempre `access_type=offline` e `prompt=consent`, come nella verifica del 2026-11-20; la sua
  assenza è comunque un errore esplicito (10-C09).
- Su Linux `keyring` può restituire un `ChainerBackend` che mescola backend sicuri e non → il
  controllo guarda ogni backend del chainer (10-C06).
- La scrittura del profilo fallisce dopo quella del portachiavi e lascia una sessione senza
  profilo → ripristino delle voci precedenti prima di rilanciare, con un test.
- Il listener reale nei test può essere instabile in CI (porte, tempi) → porta scelta dal
  sistema, browser finto in un thread con `join`, timeout brevi solo nei test del timeout.
- `respx` non intercetta `urllib` → voluto: il browser finto raggiunge il listener reale, mentre
  ogni chiamata `httpx` verso Google resta simulata; `respx` è usato con
  `assert_all_mocked=True`, quindi una chiamata non prevista fa fallire il test.
- La Gestione credenziali di Windows e il Portachiavi non si possono provare in CI → verifica
  manuale della spec sulle due postazioni, prima della chiusura.
- Il cambio del profilo predefinito del login (10-C39) sorprende chi contava su `default` →
  tocca solo chi ha `current_profile` diverso; lo dicono `docs/cli.md` e il messaggio di esito,
  che nomina il profilo scritto.
- Un test sui segreti che passa per il motivo sbagliato → prova di fallimento prevista nel task
  (vedi "Strategia di test").
