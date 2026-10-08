# 0001 – Apertura della superficie di scrittura verso Interacta

Data: 2026-10-08
Stato: accettato

## Contesto

Dalla decisione del 2026-06-04 (`ROADMAP.md`, "Versioning policy" e "Deferred / future") il
progetto ha costruito solo la superficie di **lettura** dell'API `external_v2`, un gruppo di
endpoint per minor, rimandando le scritture a dopo il completamento delle letture. Il PRD
ricostruito all'adozione del metodo (2026-10-08) ha fotografato quello stato: §1 "la superficie è
sincrona e di sola lettura", §7 "Scritture verso Interacta … fuori ambito". Il README e il sito
descrivono la libreria come `read-only`.

Il maintainer vuole le scritture a breve: le automazioni interne per cui la libreria esiste devono
anche creare e modificare post, task e anagrafiche, non solo leggerle. Il swagger pinnato
(`tests/fixtures/swagger.json`) espone **34** endpoint mutanti, non i 10 citati dalla ROADMAP, più
8 helper di lettura propedeutici (`*-data-for-create|edit|copy`,
`post-workflow-screen-data-for-edit`, `upload-new-attachment`):

| Gruppo | Endpoint | Note |
|---|---|---|
| Post e commenti | 15 | create/edit post ed event-post, custom data, allegati, watcher, screen e transizioni di workflow, copia, delete, mark-as-erasable, partecipazione a evento, commento |
| Task | 3 | create, edit, delete |
| Admin: utenti, gruppi, cataloghi e voci, workspace | 15 | utenti 4 (con credenziali), gruppi 4 (con membri), cataloghi e voci 6, workspace 1 |
| Upload allegati | 1 | URL temporaneo di storage, propedeutico agli allegati dei post |

Molti `PUT` portano un `occToken` di concorrenza ottimistica: la scrittura fallisce con `409` se la
risorsa è cambiata dalla lettura. Una scrittura verso un sistema esterno che fallisce in modo
incerto (timeout, errore di rete dopo l'invio) non è idempotente: ripeterla da soli può duplicare
un post, un commento o un utente.

## Decisione

1. La superficie di scrittura entra nell'ambito del progetto, in tutti e quattro i gruppi (post e
   commenti, task, admin, upload allegati), compresi gli helper di lettura propedeutici. L'ordine
   e il taglio delle spec si decidono spec per spec; la prima spec di scrittura parte dal gruppo
   che il maintainer sceglie.
2. Ogni scrittura è esposta con la stessa forma delle letture: façade con `.raw`, metodo con kwargs
   espliciti più variante `*_raw(req: DTO)`, comando CLI tramite `render_output`, test unit con
   `respx`, contract test, fixture JSON, pagine in `docs/`.
3. Nuova regola non negoziabile in `CLAUDE.md`: **nessuna operazione ripetuta in automatico verso
   Interacta**. Una scrittura che fallisce in modo incerto non si ritenta da sola: l'errore risale
   al chiamante con l'esito "sconosciuto"; un eventuale retry/backoff futuro vale solo per le
   letture (metodi `GET` e ricerche `POST …/data/…`).
4. La concorrenza ottimistica (`occToken`) resta a carico del chiamante: la libreria la espone e
   mappa il `409` su `ConcurrencyError`, non la risolve rileggendo e riprovando.

## Alternative considerate

- **Restare in sola lettura fino al completamento delle letture** (decisione del 2026-06-04):
  scartata, le automazioni interne hanno bisogno delle scritture prima; le letture mancanti
  (cfr. ROADMAP) si aggiungono quando servono alle scritture o a una spec dedicata.
- **Aprire solo i post e i task, lasciando l'admin fuori**: scartata dal maintainer, servono anche
  le anagrafiche (utenti, gruppi, cataloghi).
- **Retry automatico delle scritture con `occToken` o chiave di idempotenza**: scartata, l'API non
  offre chiavi di idempotenza e un retry cieco può duplicare; il chiamante decide, con l'esito
  "sconosciuto" esplicito.
- **Un pacchetto separato per le scritture**: scartata, la libreria è una e il client è unico
  (`InteractaClient`); la separazione resta a livello di risorsa (`client.posts.create(...)`).

## Conseguenze

- `specs/prd.md`: §1 non dice più "di sola lettura"; §3 aggiunge il gruppo RF-021…RF-025
  (scritture e helper propedeutici); §4 aggiunge RNF-009 (nessun retry automatico sulle scritture,
  `occToken` a carico del chiamante); §6 registra i dati personali **scritti**; §7 toglie le
  scritture e precisa il retry.
- `CLAUDE.md`: nuova regola non negoziabile (punto 3); l'introduzione non dice più "read-only
  access".
- `ROADMAP.md`: le scritture escono da "Deferred / future" ed entrano nel piano, con l'inventario
  dei 34 endpoint per gruppo; "Automatic retry/backoff" resta differito e limitato alle letture.
- `README.md` e `docs/`: descrivono ciò che è rilasciato, quindi restano `read-only` finché la prima
  spec di scrittura non va in release; quella spec li aggiorna (voce di checklist "pagine di
  `docs/`").
- Codice: nessuna modifica con questo ADR. Le spec di scrittura dovranno gestire `occToken`,
  `409 → ConcurrencyError`, l'upload in due passi (URL temporaneo, poi `PUT` del file) e la CLI
  per operazioni distruttive (`delete`, `mark-as-erasable`) con conferma esplicita.
- Diventa più facile: automazioni complete (leggi → decidi → scrivi) con un solo client. Diventa
  più difficile: la superficie pubblica cresce e la promessa "read-only" del README cade; i test
  integration opt-in dovranno usare una community di prova, mai dati reali.
