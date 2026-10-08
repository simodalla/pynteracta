# PRD – pynteracta

Origine: ricostruito dal codice il 2026-10-08 da `/sddpa:init`
Stato: bozza da confermare

Ogni sezione porta "Da confermare" finché il maintainer non la conferma; `/sddpa:specifica` chiede
di confermare le sezioni che la spec tocca. Le funzioni sono descritte per quello che il codice fa
davvero alla versione 0.9.4. Le spec per versione precedenti all'adozione del metodo stanno in
[`legacy/`](legacy/), congelate; la storia del progetto è in [`../PROGRESS.md`](../PROGRESS.md).

## 1. Scopo

*Da confermare.*

`pynteracta` è una libreria Python 3.12+ e un client a riga di comando, non ufficiali, per l'API
REST `external_v2` della piattaforma Interacta™ (Dinova S.r.l. / Maggioli S.p.A.). Serve a chi
scrive automazioni e integrazioni interne: legge utenti, post, community, cataloghi, allegati,
task, gruppi e hashtag di un tenant con tipi espliciti, paginazione pigra ed esportazione su file.
La superficie è sincrona e **di sola lettura**; le operazioni di scrittura sono rimandate
(`ROADMAP.md`, "Deferred / future").

## 2. Attori e ruoli

*Da confermare.*

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
- RF-011. Gruppi: elenco, membri di un gruppo, form di modifica.
- RF-012. Hashtag di una community.
- RF-013. Form di modifica dell'area admin (sola lettura): workspace, catalogo, voce di catalogo,
  credenziali utente.
- RF-014. Paginazione pigra: `PageIterator` e i metodi `iterate*()` seguono `nextPageToken` fino
  all'esaurimento; nella CLI `--all`, `--page-token`, `--count`.
- RF-015. Output CLI componibile: `table` (default), `json`, `yaml`; `--full` e `--fields` per la
  selezione dei campi; `--web-url` per i deep link; `--export` su csv/json/yaml/parquet, formato
  dedotto dall'estensione (`yaml` e `parquet` sono extra opzionali).
- RF-016. Configurazione: profili in `config.toml` (`platformdirs`, override con
  `PYNTERACTA_CONFIG_FILE`), variabili `PYNTERACTA_*`, flag globali della CLI; precedenza flag >
  env > file > default; comandi `config profile|add-profile|set|use-profile|remove-profile` che
  conservano commenti e formattazione del file (`tomlkit`).
- RF-017. Audit log opzionale delle chiamate API (`audit_log`), su console o su file JSON lines
  rotante (`audit_log_file`, `audit_log_max_bytes`, `audit_log_backups`); i body sono registrati
  solo con `audit_log_bodies`; `audit_log_raw` disattiva la redazione, con avviso.
- RF-018. Hook di richiesta e risposta (`ClientHooks`) che ricevono `RequestInfo` e
  `ResponseInfo`, senza tipi `httpx`.
- RF-019. Errori tipizzati: ogni stato HTTP è mappato su una sottoclasse di `InteractaError`
  (autenticazione, permessi, non trovato, validazione, concorrenza, server, trasporto), con
  stato, metodo, URL, body e `request_id`.
- RF-020. Deep link web (`WebUrls`) a post, utenti e community a partire da `base_url` e
  `base_path`.

## 4. Requisiti non funzionali

*Da confermare.* Solo ciò che il codice o la configurazione mostrano.

- RNF-001. Redazione: `Authorization`, i JWT e i campi `token|password|secret|privatekey|assertion|jwt`
  dei body sono sostituiti da `***REDACTED***` prima di log, audit log e hook (vedi P-01 nella
  linea di partenza per il caso non coperto).
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
- **Chiave del service account**: letta dal percorso configurato, mai copiata altrove; la chiave
  privata non compare nei log.
- **Conservazione**: nessuna, oltre a cache del token (fino alla scadenza) e audit log (rotazione a
  `audit_log_max_bytes` × `audit_log_backups`), entrambi a carico di chi li abilita.

## 7. Fuori ambito

*Da confermare.*

- Scritture verso Interacta (creazione o modifica di post, utenti, gruppi…), compresi gli
  endpoint "form-prep" propedeutici alle scritture.
- Client asincrono.
- Autenticazione Microsoft OAuth2 e username/password.
- Retry automatico con backoff.
- Ottenere un token Google per conto dell'utente.
- Versione 1.0 con semver stretto, finché la superficie di lettura non è completa e stabile.

## Storia del documento

- 2026-10-08: prima versione, ricostruita dal codice (v0.9.4, commit `f0398bc`).
