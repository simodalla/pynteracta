# Verifica 10 – Login Google integrato con rinnovo automatico

Data: 2026-11-21
Commit verificato: `6e74641` sul branch `m36_google_login` (spec `c7399f2`, revisioni `a226a43`,
`3b9199f`, `2df31fb`, `56c1767`; piano `a5771d3`; task `91b363c`; T01 `4ac586e`, T20 `93b27a6`,
T02 `f5e3812`, T03 `1aa3a5e`, T04 `0f6a110`, T05 `511a8f2`, T06 `ab59541`, T07 `d3f4de6`, T08
`7079d6a`, T09 `882c4cc`, T10 `9dde84f`, T11 `2a3e115`, T12 `4d72b6b`, T13 `5f87796`, T14
`410ca2e`, T15 `e7dd80b`, T16 `9dc49d8`, T17 `6fe6121`, T21 `3e1c2c7`, T22 `7a3c94e`, T18
`a69bfc6`, T19 `6e74641`)
Esito: **nessun problema**. Spec chiusa.

## Task

22 su 22 spuntati, compreso T18 (`manuale`) con l'esito compilato dal maintainer. Durante il
lavoro tre revisioni della spec, tutte scelte del maintainer:

- T01: il logout di un profilo `google_oauth2` non eliminava il file di cache, perché client e
  logout calcolavano la chiave su indirizzi diversi. Corretto nella spec: criterio 10-C41, task
  T20 (revisione `3b9199f`).
- T18: id e secret del client si possono leggere dal JSON scaricato dalla console Google
  (`--google-client-file`, `client_file=` in libreria). Compatibile con l'ADR 0002: il secret
  non passa come argomento e resta solo nel portachiavi. Criteri 10-C42–10-C45, task T21
  (revisione `2df31fb`).
- T18: `auth logout --revoke` senza `--profile` agiva in silenzio sul profilo corrente con
  service account. Ora una nota dice che non c'era nulla da revocare o eliminare. Criterio
  10-C46, task T22 (revisione `56c1767`).

Esiti della prova reale (T18), su macOS (Portachiavi) e Windows (Gestione credenziali), con il
client "Desktop" dell'ente:

- login, `auth status` e `auth whoami` riusciti su entrambe;
- sul Mac il comando dopo la scadenza del token Interacta ne ottiene uno nuovo senza browser;
- login con il file JSON riuscito senza chiedere il secret;
- dopo `auth logout --revoke` sul Mac, `auth whoami` esce `3` sia sul Mac sia su Windows.

Il rinnovo dopo la scadenza non è stato ripetuto con esito positivo su Windows, perché la revoca
è arrivata prima; lì è riuscito il rinnovo al primo comando dopo il login, che segue lo stesso
percorso.

## Tracciabilità criteri → test

| Criterio | Test | Esito |
|---|---|---|
| 10-C01 | `test_google_oauth.py::TestPkce::test_challenge_is_sha256_of_verifier`; `test_google_oauth.py::TestPkce::test_values_change_every_call`; `test_google_oauth.py::TestBuildAuthUrl::test_parameters` (+2) | verde |
| 10-C02 | `test_google_login.py::TestLogin::test_on_auth_url_when_browser_fails`; `test_google_login.py::TestLogin::test_no_browser_uses_on_auth_url_only`; `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_browser_failure_prints_url` (+1) | verde |
| 10-C03 | `test_google_login.py::TestLogin::test_full_login_with_secret_parameter`; `test_google_login.py::TestLogin::test_userinfo_without_email`; `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_full_login` (+1); prova reale T18 | verde |
| 10-C04 | `test_google_login.py::TestLogin::test_missing_client_id`; `test_google_login.py::TestLogin::test_missing_secret`; `test_cli_common.py::TestLoadJsonBody::test_configuration_error_maps_to_exit_config` (+7) | verde |
| 10-C05 | `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_missing_keyring`; `test_keychain.py::TestOpenKeychain::test_missing_keyring_names_the_extra` | verde |
| 10-C06 | `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_rejected_keychain_writes_nothing`; `test_keychain.py::TestOpenKeychain::test_rejected_backends_point_to_static_token`; `test_keychain.py::TestOpenKeychain::test_homogeneous_chainer_accepted` (+1) | verde |
| 10-C07 | `test_cli_write.py::TestReadSecret::test_interactive_prompt`; `test_cli_write.py::TestReadSecret::test_stdin_only_ignores_terminal`; `test_cli_write.py::TestReadSecret::test_empty_stdin_names_the_option` (+3) | verde |
| 10-C08 | `test_google_oauth.py::TestLoopbackReceiver::test_state_mismatch`; `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_state_mismatch` | verde |
| 10-C09 | `test_google_oauth.py::TestLoopbackReceiver::test_access_denied`; `test_google_oauth.py::TestLoopbackReceiver::test_timeout_closes_socket`; `test_google_oauth.py::TestExchangeCode::test_missing_refresh_token` (+2) | verde |
| 10-C10 | `test_google_oauth.py::TestLoopbackReceiver::test_listens_on_loopback_only`; `test_google_oauth.py::TestLoopbackReceiver::test_timeout_closes_socket`; `test_google_oauth.py::TestLoopbackReceiver::test_request_without_code_is_ignored_with_404` (+1) | verde |
| 10-C11 | `test_google_login.py::TestLogin::test_failures_leave_everything_unchanged`; `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_account_not_linked` | verde |
| 10-C12 | `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_static_token_skips_browser_and_keychain` | verde |
| 10-C13 | `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_integrated_flag_with_static_token` | verde |
| 10-C14 | `test_client.py::TestInteractaClientGoogleSession::test_session_refresh_then_exchange`; `test_cli_auth.py::TestGoogleSessionCommands::test_whoami_with_session`; prova reale T18 | verde |
| 10-C15 | `test_client.py::TestInteractaClientGoogleSession::test_near_expiry_refreshes_and_uses_new_token`; prova reale T18 | verde |
| 10-C16 | `test_client.py::TestInteractaClientGoogleSession::test_static_token_wins_over_session` | verde |
| 10-C17 | `test_client.py::TestInteractaClientGoogleSession::test_session_bound_to_tenant_and_profile`; `test_client.py::TestInteractaClientGoogleSession::test_base_url_only_never_opens_keychain` | verde |
| 10-C18 | `test_client.py::TestInteractaClientGoogleOAuth2::test_google_auth_method_without_token_raises`; `test_client.py::TestInteractaClientGoogleOAuth2::test_google_without_keyring_names_the_extra`; `test_cli_auth.py::TestGoogleSessionCommands::test_whoami_without_session_exits_3` | verde |
| 10-C19 | `test_google_login.py::TestSessionTokenProvider::test_returns_access_token_after_one_call`; `test_google_login.py::TestSessionTokenProvider::test_missing_session_at_construction`; `test_google_login.py::TestSessionTokenProvider::test_missing_entry_at_call` (+3) | verde |
| 10-C20 | `test_google_oauth.py::TestExchangeCode::test_sends_form_and_returns_tokens`; `test_google_oauth.py::TestExchangeCode::test_invalid_client`; `test_google_oauth.py::TestRefreshAccessToken::test_sends_refresh_grant` (+2) | verde |
| 10-C21 | `test_google_oauth.py::TestRefreshAccessToken::test_network_error_single_request`; `test_google_oauth.py::TestRefreshAccessToken::test_server_error_without_body`; `test_google_oauth.py::TestRefreshAccessToken::test_non_json_body` (+3) | verde |
| 10-C22 | `test_google_login.py::TestSessionTokenProvider::test_rotated_refresh_token_is_saved`; `test_google_login.py::TestSessionTokenProvider::test_session_is_reread_every_call` | verde |
| 10-C23 | `test_google_login.py::TestLogin::test_success_clears_cached_interacta_token`; `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_new_login_replaces_cached_identity` | verde |
| 10-C24 | `test_google_login.py::TestStatus::test_with_session`; `test_google_login.py::TestStatus::test_without_session`; `test_cli_auth.py::TestAuthStatus::test_table_with_session` (+4) | verde |
| 10-C25 | `test_google_login.py::TestStatus::test_service_account_profile`; `test_google_login.py::TestStatus::test_keyring_missing`; `test_google_login.py::TestStatus::test_backend_rejected` (+4) | verde |
| 10-C26 | `test_cli_auth.py::TestAuthStatus::test_check_with_valid_session`; `test_cli_auth.py::TestAuthStatus::test_check_with_rejected_session_exits_3` | verde |
| 10-C27 | `test_google_login.py::TestLogout::test_removes_session_and_cache_only_of_this_profile`; `test_google_login.py::TestLogout::test_without_session`; `test_google_login.py::TestLogout::test_without_keychain_clears_cache_and_reports` (+3) | verde |
| 10-C28 | `test_google_login.py::TestLogout::test_forget_client_secret`; `test_cli_auth.py::TestAuthLogoutGoogle::test_forget_client_secret` | verde |
| 10-C29 | `test_google_login.py::TestLogout::test_revoke_then_delete`; `test_google_login.py::TestLogout::test_revoke_failure_still_deletes`; `test_cli_auth.py::TestAuthLogoutGoogle::test_revoke` (+1); prova reale T18 | verde |
| 10-C30 | `test_google_login.py::TestLogin::test_new_secret_replaces_old_only_on_success`; `test_google_login.py::TestLogin::test_new_secret_not_saved_when_login_fails`; `test_google_login.py::TestLogin::test_replace_without_secret_is_configuration_error` (+2) | verde |
| 10-C31 | `test_google_login.py::TestLogin::test_second_profile_reuses_saved_secret`; `test_cli_auth.py::TestAuthLoginGoogleBrowser::test_second_profile_does_not_ask_secret` | verde |
| 10-C32 | `test_google_login.py::TestLogin::test_full_login_with_secret_parameter`; `test_google_login.py::TestStatus::test_with_session`; `test_google_login.py::TestLogout::test_removes_session_and_cache_only_of_this_profile` | verde |
| 10-C33 | `test_google_login.py::TestNoSecretsLeak::test_login_refresh_revoke_and_errors` | verde |
| 10-C34 | `test_google_login.py::TestNoSecretsLeak::test_login_refresh_revoke_and_errors`; `test_transport.py::TestRequestExternal::test_post_form_to_absolute_url`; `test_transport.py::TestRequestExternal::test_get_with_bearer` (+4) | verde |
| 10-C35 | `test_google_login.py::TestNoSecretsLeak::test_login_refresh_revoke_and_errors` | verde |
| 10-C36 | `test_google_oauth.py::TestLoopbackReceiver::test_result_page_has_no_secrets_and_nothing_is_logged` | verde |
| 10-C37 | `test_keychain.py::TestPackaging::test_keyring_only_in_google_extra`; `test_keychain.py::TestPackaging::test_imports_without_keyring`; `test_keychain.py::TestPackaging::test_service_account_whoami_without_keyring` | verde |
| 10-C38 | `test_docs_snippets.py::test_google_login_pages`; `uv run mkdocs build --strict` | verde |
| 10-C39 | `test_config.py::TestResolveProfileName::test_given_name_wins`; `test_config.py::TestResolveProfileName::test_current_profile`; `test_config.py::TestResolveProfileName::test_default_without_file` (+3) | verde |
| 10-C40 | `test_client.py::TestInteractaClientGoogleOAuth2::test_current_profile_names_the_cache_key`; `test_client.py::TestInteractaClientGoogleSession::test_current_profile_session` | verde |
| 10-C41 | `test_auth.py::TestGoogleCacheKey::test_cache_api_base_sets_the_key`; `test_auth.py::TestGoogleCacheKey::test_without_cache_api_base_uses_transport_base`; `test_auth.py::TestGoogleCacheKey::test_legacy_google_cache_key` (+2) | verde |
| 10-C42 | `test_google_oauth.py::TestReadClientFile::test_desktop_client`; `test_google_oauth.py::TestReadClientFile::test_accepts_str_path`; `test_google_login.py::TestLoginClientFile::test_login_with_client_file` (+4) | verde |
| 10-C43 | `test_google_oauth.py::TestReadClientFile::test_invalid_file`; `test_google_oauth.py::TestReadClientFile::test_wrong_types_are_rejected`; `test_google_oauth.py::TestReadClientFile::test_not_logged` (+2) | verde |
| 10-C44 | `test_google_login.py::TestLoginClientFile::test_file_and_secret_together`; `test_google_login.py::TestLoginClientFile::test_mismatching_client_id`; `test_google_login.py::TestLoginClientFile::test_matching_client_id` (+3) | verde |
| 10-C45 | `test_google_login.py::TestLoginClientFile::test_login_with_client_file`; `test_google_login.py::TestLoginClientFile::test_invalid_file`; `test_google_login.py::TestLoginClientFile::test_file_and_secret_together` | verde |
| 10-C46 | `test_cli_auth.py::TestAuthLogoutNothingToDo::test_revoke_on_service_account_profile`; `test_cli_auth.py::TestAuthLogoutNothingToDo::test_revoke_on_google_profile_without_session`; `test_cli_auth.py::TestAuthLogoutNothingToDo::test_forget_client_secret_without_secret` (+2) | verde |

46 criteri su 46 con almeno un test; 10-C03, 10-C14, 10-C15 e 10-C29 anche con la prova reale
(T18). Nessun marker cita un criterio inesistente. Il conteggio "(+n)" indica gli altri test che
citano lo stesso criterio.

## Controlli automatici

| Comando | Esito |
|---|---|
| `uv run ruff check .` | verde |
| `uv run ruff format --check .` | verde (143 file) |
| `uv run mypy src` | verde (67 file) |
| `uv run pytest -m "not integration and not contract"` | verde (1869 test, 106 snapshot) |
| `uv run pytest -m contract` | verde (238 test) |
| `uv run mkdocs build --strict` | verde, nessun warning |
| `uv run pre-commit run --all-files` | verde |

Nessun controllo a cricchetto configurato. I test di integrazione non toccano il login integrato
(nessuna variabile nuova in `tests/integration/.env.example`); il flusso reale è coperto da T18.

## Copertura

| Ambito | Linea di partenza | Ora |
|---|---|---|
| Totale | 96,18 % | **96,51 %** (7354/7620 righe) |
| `api` | 98,45 % | 98,45 % |
| `cli` | 95,29 % | 95,79 % |
| `models/facade` | 96,39 % | 96,39 % |
| `auth.py` | 94,01 % | 94,04 % |
| `client.py` | 96,70 % | 98,17 % |
| `config.py` | 98,86 % | 100 % |
| `transport.py` | 98,73 % | 98,82 % |
| `logging.py` | 94,74 % | 97,64 % (dal fix `3467a26` fuori milestone, non da questa spec) |

File toccati dalla spec, soglia 85 %:

| File | Copertura | Righe scoperte |
|---|---|---|
| `keychain.py` (nuovo) | 93 % | 81-82, 125-126 (rami difensivi del backend `chainer` e dell'errore di `delete`) |
| `google_oauth.py` (nuovo) | 99 % | 210-212 (errore del socket alla chiusura del listener) |
| `google_login.py` (nuovo) | 96 % | 69-70, 72, 158-160, 171-172, 180, 211 (sessione illeggibile, profilo non risolvibile, eccezione di `webbrowser`, utente senza dati) |
| `transport.py` | 99 % | 349-350 (preesistenti) |
| `client.py` | 98 % | 101-102 (preesistenti) |
| `auth.py` | 94 % | 51-58, 63, 79, 104, 262-263, 315-317, 396, 426-427, 441, 550-551, 559 (preesistenti, nessuna in `clear_cached_token` né nella chiave di cache Google) |
| `config.py` | 100 % | – |
| `exceptions.py` | 100 % | – |
| `cli/auth.py` | 96 % | 152-153, 179-181, 365, 377-381, 437 (rami del login con token statico e del service account, preesistenti) |
| `cli/_common.py` | 94 % | preesistenti, nessuna nella mappatura di `ConfigurationError` |
| `cli/_write.py` | 100 % | – |

La linea di partenza è aggiornata (totale, aree, file, conteggi dei controlli).

## Regole non negoziabili

| Regola | Verifica | Esito |
|---|---|---|
| Token e segreti mai nei log | Le chiamate a Google passano da `request_external`: metodo, URL e stato in log, audit e hook, mai i corpi, anche con `audit_log_bodies` e `audit_log_raw` (10-C34). Gli errori di Google portano solo `error` ed `error_description`. Il test di 10-C33 (`TestNoSecretsLeak`) usa valori sentinella per refresh token, codice, verificatore, id token, secret e access token, con audit, hook e log attivi; è stato visto fallire togliendo una protezione alla volta (form in log, corpo della risposta, corpo intero nell'errore, email in un evento). La lettura del file del client non riporta mai il contenuto, nemmeno nella catena delle eccezioni (10-C43, visto fallire con due regressioni). Il listener non registra le richieste (10-C36). | rispettata |
| Cache del token con permessi stretti | `FileTokenCache` invariata; la chiave resta per tenant (10-C41 la allinea per i profili Google). | rispettata |
| Segreti di lunga durata solo nel portachiavi | Refresh token e client secret passano solo da `Keychain`; i backend assenti o in chiaro su file sono rifiutati, senza ripiego (10-C06); nessuna opzione della CLI accetta il secret come valore (10-C07); il file JSON del client è letto e non copiato, e il suo percorso non è salvato (10-C42). | rispettata |
| Segreti fuori dal repository | Fixture e documentazione usano valori finti e riconoscibili (`000000000000-example…`, `GOCSPX-example-not-a-secret`, `1//example-refresh-token`); nessun id o secret del client dell'ente nel codice né nei file versionati; gli esiti di T18 non riportano token né segreti. | rispettata |
| Soglie che non scendono | Copertura totale e per area in salita; regole di ruff e mypy invariate. | rispettata |
| Dati personali fuori dai log | L'email dell'account Google sta nel portachiavi e compare solo nell'output di `auth status`, mai nei log (10-C35); `GoogleLoginResult` la esclude dal `repr`. | rispettata |
| Nessuna operazione ripetuta in automatico | Ogni chiamata a Google è una sola richiesta; timeout ed errori di rete risalgono come `TransportError` (10-C21). | rispettata |
| Canale stdio del server MCP | Non applicabile: il server arriva con la spec 11. Il login non scrive sullo standard output di suo (10-C32). | non applicabile |

## Coerenza

- Il codice fa ciò che dicono spec e piano, nella versione rivista: login dal browser con PKCE e
  listener su loopback, sessione per profilo e tenant nel portachiavi, rinnovo senza browser,
  `auth status [--check]`, `auth logout [--forget-client-secret] [--revoke]` con le note di
  10-C46, `--google-client-file`, profilo corrente come predefinito dei login e del client,
  funzioni pubbliche in `pynteracta.google_login`, extra `pynteracta[google]`.
- ADR 0002 copre la decisione; i "Requisiti nuovi" sono nel PRD (`6e74641`): RF-026a…RF-026g,
  RF-016a, RF-016b, RNF-012a, RNF-001c; RF-026, RNF-012 e l'estensione di RNF-001 risultano
  realizzati; §5 e §6 aggiornati; §2, §5, §6 e §7 riconfermati.
- `CLAUDE.md` aggiornato (mappa dei moduli, ambito, Stack); `README.md` e `docs/index.md`
  descrivono il login dal browser e l'extra, senza numeri di versione (T17).

## Debiti aperti della linea di partenza

Nessuna violazione `P-<mm>` aperta; nessun controllo a cricchetto. Copertura misurata.

## Problemi trovati

Nessuno nella spec. Osservazioni fuori ambito, da seguire a parte:

- Senza configurazione, structlog stampa i log della libreria sullo standard output. Riguarda
  tutta la libreria, non solo questa spec; per il server MCP della spec 11, dove lo stdout è
  riservato al protocollo (RNF-013), va deciso come configurare i log.
- Durante la prova, un comando lanciato in background non ha scritto le righe di log nel file
  d'uscita, mentre in un terminale interattivo comparivano: da capire se dipende dalla
  configurazione del logging della CLI quando l'output non è un terminale.
- Il livello di log della CLI viene dal profilo corrente anche quando `auth login --profile`
  lavora su un altro profilo: comportamento precedente alla spec.
- `auth status` in tabella tronca i valori lunghi nei terminali stretti; con `--output json`
  sono interi.
