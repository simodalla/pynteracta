# PRD – pynteracta

Origine: ricostruito dal codice il 2026-10-08 da `/sddpa:init`
Stato: bozza da confermare

Ogni sezione porta "Da confermare" finché il maintainer non la conferma; `/sddpa:specifica` chiede
di confermare le sezioni che la spec tocca. Le funzioni sono descritte per quello che il codice fa
davvero alla versione 0.9.4. Le spec per versione precedenti all'adozione del metodo stanno in
[`legacy/`](legacy/), congelate; la storia del progetto è in [`../PROGRESS.md`](../PROGRESS.md).

## 1. Scopo

Confermato dal maintainer il 2026-10-08.

`pynteracta` è una libreria Python 3.12+ e un client a riga di comando, non ufficiali, per l'API
REST `external_v2` della piattaforma Interacta™ (Dinova S.r.l. / Maggioli S.p.A.). Serve a chi
scrive automazioni e integrazioni interne: legge utenti, post, community, cataloghi, allegati,
task, gruppi e hashtag di un tenant con tipi espliciti, paginazione pigra ed esportazione su file.
Ha inoltre due usi voluti: essere la libreria che gli strumenti di *vibe coding* (agenti di
programmazione assistita) usano per lavorare con Interacta, quindi con un'API tipizzata, uniforme e
documentata che un agente possa scoprire e comporre; ed essere la base di un **server MCP non
ufficiale per Interacta**, che ne esporrà le operazioni come strumenti.
La superficie è sincrona. Alla versione 0.9.4 è di sola lettura; con
[ADR 0001](adr/0001-apertura-della-superficie-di-scrittura.md) le scritture (post e commenti,
task, anagrafiche admin, upload di allegati) entrano nell'ambito e arrivano con le prossime spec.

## 2. Attori e ruoli

Confermato dal maintainer il 2026-10-08.

| Attore | Ruolo o gruppo | Cosa può fare |
|---|---|---|
| Sviluppatore di integrazioni | usa la libreria da Python | istanzia `InteractaClient`, chiama le risorse `client.<risorsa>.*`, registra hook, legge gli errori tipizzati |
| Operatore | usa la CLI `pynteracta` | configura profili, si autentica, interroga ed esporta dati di lettura |
| Service account Interacta | identità tecnica del tenant | firma l'asserzione JWT (RS512) con cui la libreria ottiene l'access token; vede ciò che il tenant gli concede |
| Utente Google | identità personale già collegata a un utente Interacta | fornisce un access token Google che la libreria scambia con un access token Interacta |
| Tenant Interacta | sistema esterno | espone l'API `external_v2`; decide visibilità e permessi, che la libreria non aggira |

## 3. Requisiti funzionali

*Da confermare.* Uno per funzione; il dettaglio arriva con le spec che li toccano.

- RF-001. Autenticazione con service account: da un file chiave JSON (`ServiceAccountKey`) la
  libreria costruisce un'asserzione JWT firmata RS512 e ottiene un access token dal tenant.
- RF-002. Autenticazione Google OAuth2: un access token Google (scope minimo `profile`), fornito
  dall'utente, viene scambiato con un access token Interacta.
- RF-003. Ciclo di vita del token: cache su file (`FileTokenCache`) o in memoria
  (`MemoryTokenCache`), refresh anticipato di 60 s rispetto alla scadenza, invalidazione quando il
  server rifiuta il token, chiave di cache distinta per tenant.
- RF-004. Identità corrente: dati dell'utente autenticato (`auth whoami`, `users me`,
  `users profile`).
- RF-005. Utenti: elenco paginato con filtri (stato, provider di login, manager, lingua, prefissi
  di nome ed email…) e ordinamento, iterazione su tutte le pagine, form di modifica
  (`get_for_edit`).
- RF-006. Post: dettaglio per id e per client uid, capabilities, storia degli eventi, stream
  globale, elenco in community con filtri su campi standard, custom e di workflow (validazione
  opzionale contro la definizione dei post della community) e ordinamento, controllo di visibilità
  con e senza commenti, elenco dei commenti.
- RF-007. Community: elenco, dettagli singoli e in blocco, definizione dei post (singola e
  multipla).
- RF-008. Cataloghi: elenco dei cataloghi e delle voci, con iterazione.
- RF-009. Allegati: elenco per post, dettaglio per id, controllo di visibilità.
- RF-010. Task: dettaglio per id.
  - RF-022a. La lettura di un task espone `occ_token`, il token di concorrenza da passare alla
    modifica. *(Spec 02, 2026-10-08.)*
- RF-011. Gruppi: elenco, membri di un gruppo, form di modifica.
- RF-012. Hashtag di una community.
- RF-013. Form di modifica dell'area admin (sola lettura): workspace, catalogo, voce di catalogo,
  credenziali utente.
- RF-014. Paginazione pigra: `PageIterator` e i metodi `iterate*()` seguono `nextPageToken` fino
  all'esaurimento; nella CLI `--all`, `--page-token`, `--count`.
- RF-015. Output CLI componibile: `table` (default), `json`, `yaml`; `--full` e `--fields` per la
  selezione dei campi; `--web-url` per i deep link; `--export` su csv/json/yaml/parquet, formato
  dedotto dall'estensione (`yaml` e `parquet` sono extra opzionali).
  - RF-015a. La CLI termina con exit code `9` quando una scrittura fallisce per conflitto di
    concorrenza (`409`), distinto dagli altri errori. *(Spec 02, 2026-10-08.)*
- RF-016. Configurazione: profili in `config.toml` (`platformdirs`, override con
  `PYNTERACTA_CONFIG_FILE`), variabili `PYNTERACTA_*`, flag globali della CLI; precedenza flag >
  env > file > default; comandi `config profile|add-profile|set|use-profile|remove-profile` che
  conservano commenti e formattazione del file (`tomlkit`).
- RF-017. Audit log opzionale delle chiamate API (`audit_log`), su console o su file JSON lines
  rotante (`audit_log_file`, `audit_log_max_bytes`, `audit_log_backups`); i body sono registrati
  solo con `audit_log_bodies`; `audit_log_raw` disattiva la redazione sul solo canale di logging,
  con avviso. *(Confermato dal maintainer il 2026-10-08, spec 01.)*
- RF-018. Hook di richiesta e risposta (`ClientHooks`) che ricevono `RequestInfo` e
  `ResponseInfo`, senza tipi `httpx`. *(Confermato dal maintainer il 2026-10-08, spec 01.)*
- RF-019. Errori tipizzati: ogni stato HTTP è mappato su una sottoclasse di `InteractaError`
  (autenticazione, permessi, non trovato, validazione, concorrenza, server, trasporto), con
  stato, metodo, URL, body e `request_id`.
- RF-020. Deep link web (`WebUrls`) a post, utenti e community a partire da `base_url` e
  `base_path`.

Scritture, decise con [ADR 0001](adr/0001-apertura-della-superficie-di-scrittura.md): ogni spec
che le realizza ne precisa i dettagli (RF-022 dalla [spec 02](02-task-write/spec.md), 0.10.0; le
altre non ancora implementate). Stessa forma delle letture (façade con `.raw`, kwargs espliciti
più `*_raw`, comando CLI, test unit e contract).

- RF-021. Post e commenti: creazione e modifica di post e post-evento (dati, campi custom,
  allegati, watcher, dati di screen del workflow), transizione di workflow, copia, eliminazione e
  marcatura per cancellazione, risposta di partecipazione a un evento, creazione di commenti; con
  gli helper di lettura propedeutici (`post-data-for-create|edit|copy`, `event-post-data-for-*`,
  `post-workflow-screen-data-for-edit`).
- RF-022. Task: creazione, modifica, eliminazione. La libreria invia solo i campi passati, in una
  sola richiesta; `edit` riceve l'`occToken` dal chiamante. Il server tratta la modifica come una
  sostituzione (i campi omessi sono azzerati, tranne watcher e allegati, che hanno coppie
  add/remove) ed esige assegnatario e scadenza: lo dice la documentazione, la libreria non aggiunge
  nulla da sola. *(Confermato dal maintainer il 2026-10-08, spec 02.)*
- RF-023. Anagrafiche admin: creazione, modifica, eliminazione e credenziali degli utenti;
  creazione, modifica, eliminazione e membri dei gruppi; creazione, modifica e flag `deleted` di
  cataloghi e voci; modifica del workspace.
- RF-024. Upload di allegati: richiesta di un URL temporaneo di storage e caricamento del file,
  propedeutico agli allegati dei post.
- RF-025. Concorrenza ottimistica: dove l'API richiede un `occToken`, la libreria lo espone al
  chiamante e mappa il `409` su `ConcurrencyError`; non rilegge e non riprova da sola. Le
  operazioni distruttive nella CLI chiedono conferma esplicita. *(Confermato dal maintainer il
  2026-10-08, spec 02.)*
  - RF-025a. `tasks delete` (e i comandi distruttivi futuri) chiede conferma mostrando id e titolo;
    `--yes` la salta; senza terminale interattivo e senza `--yes` il comando rifiuta con exit code
    `2` e non invia nulla. *(Spec 02, 2026-10-08.)*
  - RF-025b. `tasks edit` modifica solo i campi indicati: rilegge il task e rimanda gli altri,
    perché il server sostituisce il task intero; `--occ-token` impone solo il token. *(Spec 02,
    2026-10-08, dopo la prova sul tenant.)*

## 4. Requisiti non funzionali

*Da confermare.* Solo ciò che il codice o la configurazione mostrano.

- RNF-001. Redazione prima di log, audit log e hook, dentro il transport: gli header
  `Authorization`, `Proxy-Authorization` e quelli il cui nome contiene `token`, `secret`,
  `password` o `api-key` perdono l'intero valore; in `Cookie` e `Set-Cookie` ogni cookie perde il
  valore e conserva nome e attributi (un header cookie non analizzabile con certezza è redatto per
  intero); i JWT sono sostituiti ovunque; i campi `token|password|secret|privatekey|assertion|jwt`
  dei body sono sostituiti da `***REDACTED***`. *(Confermato dal maintainer il 2026-10-08;
  precisato dalla spec 01, che chiude P-01.)*
- RNF-002. Cache del token su file con permessi POSIX stretti (`0o600` file, `0o700` cartella),
  lettura rifiutata se più larghi; su Windows avviso una tantum e raccomandazione di
  `token_cache = "memory"`.
- RNF-003. Tipizzazione completa: `py.typed`, `mypy --strict`, modelli pydantic v2 generati dal
  swagger pinnato (`datamodel-code-generator`) e façade a mano con `extra="ignore"` e `.raw` per
  la compatibilità in avanti.
- RNF-004. Python ≥ 3.12, client sincrono (`httpx.Client`); nessun client asincrono.
- RNF-005. La libreria non configura il logging a import: `structlog.configure()` solo dentro
  `setup_default_logging()`, chiamata solo dalla CLI.
- RNF-006. Qualità misurata in CI: ruff (lint e formato), mypy strict, unit test su Python 3.12 e
  3.13 con copertura ≥ 85 %, contract test contro il swagger, build della distribuzione e del sito.
- RNF-007. Licenza Apache-2.0 con intestazione SPDX su ogni sorgente; distribuzione su PyPI via
  trusted publishing (OIDC), senza token nel repository.
- RNF-008. Timeout configurabile (`timeout_seconds`, default 30 s); nessun retry automatico.
- RNF-009. Nessuna operazione ripetuta in automatico verso Interacta (ADR 0001, regola non
  negoziabile): una scrittura che fallisce in modo incerto (timeout, errore di rete) non si ritenta
  da sola, l'errore risale al chiamante con esito sconosciuto; un futuro retry/backoff vale solo
  per le letture. *(Confermato dal maintainer il 2026-10-08, spec 02.)*
- RNF-010. Le date-ora di scrittura (`expiration`) accettano solo `datetime` con fuso orario e
  arrivano al server come data-ora locale più nome IANA del fuso (offset fisso → UTC); la CLI
  interpreta i valori senza offset nel fuso `--timezone` (predefinito `Europe/Rome`). *(Spec 02,
  2026-10-08.)*

## 5. Integrazioni esterne

*Da confermare.*

| Sistema | Uso | Come si collega |
|---|---|---|
| Interacta REST API `external_v2` | tutte le letture | HTTPS verso `{base_url}{base_path}/api/external/v{api_version}/`, header `Authorization: Bearer <token>` e `User-Agent: pynteracta/<versione>` |
| Interacta auth (`core/auth`) | ottenere l'access token | `create-access-token-by-service-account` con asserzione JWT RS512; `create-access-token-by-google-oauth2-access-token-credentials` con token Google |
| Google OAuth2 | identità personale | il token lo procura l'utente fuori dalla libreria; la libreria lo inoltra una sola volta per lo scambio |
| PyPI, GitHub Releases, GitHub Pages | distribuzione e documentazione | solo in CI, su tag `v*` e push su `main`; nessun uso a runtime |

## 6. Dati personali trattati

*Da confermare.*

- **Dati letti dal tenant**: anagrafiche degli utenti Interacta (nome, cognome, email, id, stato,
  provider di login), contenuti di post, commenti, allegati e task, membri dei gruppi. La libreria
  li restituisce al chiamante e, nella CLI, li stampa o li esporta su file **scelti
  dall'operatore**; non li conserva.
- **Dati scritti su disco dalla libreria**: il token di accesso (cache su file, permessi stretti,
  cartella utente); il file di configurazione (URL del tenant, percorso della chiave, profili);
  l'audit log, solo se abilitato, che contiene URL, header redatti e, con `audit_log_bodies`, i
  body delle risposte e quindi i dati personali sopra elencati (eccezione documentata nelle
  Regole non negoziabili del `CLAUDE.md`).
- **Dati scritti sul tenant** (dalle spec di scrittura, ADR 0001): anagrafiche di utenti
  (compresi i dati di credenziale), appartenenze ai gruppi, contenuti di post, commenti, task e
  allegati forniti dal chiamante. La libreria li inoltra al tenant così come li riceve; non li
  conserva e non li logga (eccezione: audit log con `audit_log_bodies`, come sopra). *(Confermato
  dal maintainer il 2026-10-08, spec 02: titolo e descrizione dei task, id di assegnatari e
  watcher.)*
- **Chiave del service account**: letta dal percorso configurato, mai copiata altrove; la chiave
  privata non compare nei log.
- **Conservazione**: nessuna, oltre a cache del token (fino alla scadenza) e audit log (rotazione a
  `audit_log_max_bytes` × `audit_log_backups`), entrambi a carico di chi li abilita.

## 7. Fuori ambito

*Da confermare.*

- Client asincrono.
- Autenticazione Microsoft OAuth2 e username/password.
- Retry automatico con backoff sulle scritture (vedi RNF-009); sulle letture è solo rimandato.
- Risoluzione automatica dei conflitti di concorrenza (`occToken`): spetta al chiamante.
- Ottenere un token Google per conto dell'utente.
- Versione 1.0 con semver stretto, finché la superficie di lettura non è completa e stabile.

## Storia del documento

- 2026-10-08: prima versione, ricostruita dal codice (v0.9.4, commit `f0398bc`).
- 2026-10-08: apertura della superficie di scrittura (§1, RF-021…RF-025, RNF-009, §6, §7), vedi
  [ADR 0001](adr/0001-apertura-della-superficie-di-scrittura.md).
- 2026-10-08: §1 e §2 confermati dal maintainer; §1 aggiunge gli usi da strumenti di vibe coding e
  come base di un server MCP non ufficiale.
- 2026-10-08: RNF-001 precisato dalla [spec 01](01-redazione-cookie-header/spec.md) (cookie e
  header redatti per nome); RF-017, RF-018 e RNF-001 confermati dal maintainer.
- 2026-10-08: [spec 02](02-task-write/spec.md) (scrittura dei task, 0.10.0): RF-022 precisato con
  la semantica del server; nuovi RF-022a, RF-015a, RF-025a, RF-025b, RNF-010; RF-022, RF-025,
  RNF-009 e la voce "Dati scritti sul tenant" di §6 confermati dal maintainer.
