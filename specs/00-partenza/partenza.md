# 00 – Linea di partenza

Data: 2026-10-08
Commit: `f0398bc` sul branch `main`
Scritta da: `/sddpa:init` (plugin `sddpa` 0.3.0)

Fotografia del progetto al momento dell'adozione del metodo. Le spec non possono peggiorare questi
numeri; `/sddpa:verifica` li aggiorna quando migliorano. Non si modifica a mano.

## Controlli bloccanti

| Comando | Esito |
|---|---|
| `uv run ruff check .` | verde ("All checks passed!") |
| `uv run ruff format --check .` | verde (104 file già formattati) |
| `uv run mypy src` | verde (52 file, nessun errore) |
| `uv run pytest -m "not integration and not contract"` | verde (751 test, 67 snapshot; 717 all'adozione) |
| `uv run pytest -m contract` | verde (87 test) |

Esclusi dai controlli del metodo: `uv run pytest -m integration` (20 test opt-in contro un tenant
reale, si auto-skippano senza `tests/integration/.env` e `.secrets/sa.json`) e `uv build` (solo in
release).

## Controlli a cricchetto

Nessuno: lint e tipi sono verdi, quindi sono bloccanti.

## Copertura

Misurata con `uv run pytest -m "not integration and not contract" --cov --cov-report=term-missing`
(solo unit test, come la CI; `models/generated/` escluso dalla misura). "Modulo" è il primo livello
sotto `src/pynteracta/`.

| Ambito | Copertura |
|---|---|
| Totale | 93,18 % (3865/4148 righe; 93,15 % all'adozione) |
| `api` | 96,02 % |
| `cli` | 89,31 % |
| `models/facade` | 94,74 % |
| `auth.py` | 94,01 % |
| `client.py` | 96,70 % |
| `config.py` | 98,86 % |
| `logging.py` | 94,39 % (101/107; 93,41 % all'adozione) |
| `pagination.py` | 93,02 % |
| `transport.py` | 97,84 % |
| `exceptions.py`, `hooks.py`, `urls.py`, `__init__.py` | 100 % |

Il file meno coperto è `cli/communities.py` (53 %).

## Violazioni note delle regole non negoziabili

Trovate con una ricerca ragionevole nel codice e confermate dal maintainer, non con un audit
completo.

| Id | Regola | Dove | Descrizione | Stato |
|---|---|---|---|---|
| P-01 | Token e segreti mai nei log | `src/pynteracta/logging.py` (`redact_headers`) | Redigeva solo `Authorization` e i valori a forma di JWT. L'header `Set-Cookie` della risposta di login porta `interacta_auth_refresh_token=<hex>`, che non è un JWT: con l'audit log attivo finiva in chiaro negli header di `audit.response`. v0.9.3 aveva redatto body e header ma non copriva questo caso. | **chiusa** dalla [spec 01](../01-redazione-cookie-header/spec.md) il 2026-10-08 (commit `1129894`) |

Nessuna violazione aperta.

## Cosa fa già l'applicazione

Indice delle funzioni esistenti, con il modulo e il requisito del PRD ([prd.md](../prd.md)).

- Autenticazione con service account (JWT RS512 → access token) – `auth.py`, `client.py` – RF-001
- Autenticazione Google OAuth2 (scambio di un access token Google) – `client.py`, `api/auth.py` – RF-002
- Cache del token su file o in memoria, con scadenza, refresh e chiave per tenant – `auth.py` – RF-003
- Identità corrente (`auth whoami`, `users me`, `users profile`) – `api/auth.py`, `api/users.py` – RF-004
- Utenti: elenco con filtri e ordinamento, iterazione, form di modifica – `api/users.py`, `cli/users.py` – RF-005
- Post: dettaglio, per client uid, capabilities, storia, stream globale, elenco in community con filtri su campi custom e di workflow (validazione opzionale), visibilità, commenti – `api/posts.py`, `models/facade/post_filters.py`, `cli/posts.py` – RF-006
- Community: elenco, dettagli singoli e bulk, definizioni dei post – `api/communities.py`, `cli/communities.py` – RF-007
- Cataloghi: elenco e voci, con iterazione – `api/catalogs.py`, `cli/catalogs.py` – RF-008
- Allegati: elenco per post, dettaglio, visibilità – `api/attachments.py`, `cli/attachments.py` – RF-009
- Task: dettaglio – `api/tasks.py`, `cli/tasks.py` – RF-010
- Gruppi: elenco, membri, form di modifica – `api/groups.py`, `cli/groups.py` – RF-011
- Hashtag di una community – `api/hashtags.py`, `cli/hashtags.py` – RF-012
- Form di modifica admin: workspace, catalogo, voce di catalogo, credenziali utente – `api/admin_manage.py`, `cli/admin_manage.py` – RF-013
- Paginazione pigra (`PageIterator`, `iterate*()`, `--all`, `--page-token`, `--count`) – `pagination.py` – RF-014
- Output CLI `table`/`json`/`yaml`, `--full`, `--fields`, `--web-url`, `--export` csv/json/yaml/parquet – `cli/_common.py`, `cli/_export.py` – RF-015
- Configurazione a profili (TOML, env `PYNTERACTA_*`, flag) e comandi `config` – `config.py`, `cli/config.py` – RF-016
- Audit log opzionale su console o file JSON lines rotante, body opt-in – `logging.py`, `transport.py` – RF-017
- Hook di richiesta e risposta senza tipi `httpx` – `hooks.py`, `transport.py` – RF-018
- Mappatura degli errori HTTP sulla gerarchia `InteractaError` – `exceptions.py`, `transport.py` – RF-019
- Deep link web a post, utenti e community – `urls.py` – RF-020

## Storia

| Data | Spec | Cosa è cambiato |
|---|---|---|
| 2026-10-08 | – | Linea di partenza iniziale |
| 2026-10-08 | 01 | P-01 chiusa; copertura totale 93,15 % → 93,18 %, `logging.py` 93,41 % → 94,39 %; unit test 717 → 751 |
