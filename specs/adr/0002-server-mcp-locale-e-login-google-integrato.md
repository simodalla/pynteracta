# 0002 – Server MCP locale e login Google integrato

Data: 2026-11-20
Stato: accettato

## Contesto

Il PRD (§1) prevede già che la libreria sia "la base di un server MCP non ufficiale per
Interacta", ma non dice dove vive quel server, con quale identità agisce né quali operazioni
espone. Il maintainer vuole ora usare Interacta da Claude e da altri agenti LLM: leggere post,
community e cataloghi, e creare o aggiornare task a partire da ciò che legge.

Tre fatti del progetto, oggi, ostacolano questo uso.

1. **Il token Google lo procura l'utente.** RF-002 e §5 dicono che l'access token Google è
   "fornito dall'utente"; §7 mette fuori ambito "ottenere un token Google per conto dell'utente";
   `docs/authentication.md` dichiara che la libreria non esegue alcun flusso di login. Il token
   dura circa un'ora e non viene mai salvato (`Profile.google_oauth2_token`). Un server MCP è un
   processo lungo, avviato dal client MCP e collegato via stdio: non può chiedere un token
   all'utente, e con un token statico smette di funzionare dopo un'ora.
2. **L'identità tecnica è troppo larga per un agente.** Con il service account il modello vedrebbe
   e farebbe tutto ciò che il tenant concede al service account, per chiunque usi il server. Con
   l'identità personale i permessi di Interacta limitano l'agente a ciò che la persona può già
   fare.
3. **Un agente si comporta diversamente da uno script.** Legge testo scritto da altri (post e
   commenti), che può contenere istruzioni malevole; tende a riprovare quando riceve un errore,
   mentre la regola non negoziabile di ADR 0001 vieta di ripetere le scritture; non ha un
   terminale su cui confermare un'operazione distruttiva (RF-025a vale per la CLI).

Sui task l'API `external_v2` offre quattro endpoint: dettaglio per id, creazione su un post,
modifica (con `occToken`) ed eliminazione. Non esiste un elenco dei task di un utente: il post
espone solo `tasksCount`, l'elenco dei post di una community ha il filtro
`toManageStandardTasks`, e gli id dei task compaiono negli eventi della storia del post.

## Decisione

1. **Il server MCP entra nell'ambito, dentro questo pacchetto.** Si avvia con
   `pynteracta mcp serve`, è distribuito come extra opzionale (`pynteracta[mcp]`) e parla solo il
   trasporto **stdio**, in locale, sulla macchina della persona. Il server remoto (HTTP) resta
   fuori ambito.
2. **Il server agisce con l'identità del profilo; quella prevista è personale.** L'uso voluto e
   documentato è Google OAuth2: i permessi restano quelli che Interacta dà alla persona. Un
   profilo con service account è accettato con un avviso (confermato dal maintainer il
   2026-11-20): il server parte, segnala sullo standard error che agisce con un'identità tecnica
   e lo rende visibile anche al client, nello strumento che restituisce l'identità corrente,
   perché lo standard error di un server MCP di norma non arriva alla persona.
3. **Letture curate, mai l'area admin.** Il server espone un insieme ridotto di strumenti di
   lettura pensati per intento (identità corrente, community, post, storia, commenti, allegati,
   cataloghi, hashtag, dettaglio di un task), con output ridotto e paginazione limitata. Non
   espone gli endpoint `admin/*` né gli elenchi di utenti e gruppi.
4. **Scritture solo sui task, e solo su richiesta.** Creazione, modifica ed eliminazione dei task
   sono registrate come strumenti solo se il server parte con un flag esplicito
   (`--enable-task-writes`); senza flag il modello non le vede. Nessun'altra scrittura è esposta.
   Allargare le scritture del server ad altri gruppi richiede una spec che citi questo ADR;
   esporre l'area admin richiede un nuovo ADR.
5. **Le regole sulle scritture valgono anche per il server.** Nessun retry: un esito incerto
   torna al modello come "esito sconosciuto, non ripetere". Un `409` torna come conflitto di
   concorrenza e non si risolve rileggendo e riprovando. L'eliminazione è dichiarata distruttiva
   nelle annotazioni MCP, perché sia il client a chiedere conferma alla persona.
6. **Il login Google diventa una funzione della libreria.** `pynteracta auth login --google`
   esegue il flusso OAuth2 per applicazioni installate (authorization code con PKCE e redirect
   su loopback) con un client OAuth dell'organizzazione, con lo scope minimo necessario allo
   scambio (`email`, verificato sul tenant il 2026-11-20: `profile` da solo è rifiutato). La
   libreria conserva il refresh token e rinnova da sola l'access token
   Google quando deve ripetere lo scambio con Interacta. Il token statico (`--google-token`,
   `PYNTERACTA_GOOGLE_OAUTH2_TOKEN`, `google_token`, `google_token_provider`) resta valido.
7. **Il refresh token sta nel portachiavi di sistema.** Le postazioni sono macOS e Windows
   (confermato dal maintainer il 2026-11-20): Portachiavi di macOS e Gestione credenziali di
   Windows. Mai in `config.toml`, mai in un file in chiaro, mai nei log. Se il portachiavi non è
   disponibile (per esempio Linux senza sessione grafica) il login integrato fallisce con un
   messaggio chiaro, senza ripiegare in silenzio su un file. Anche il client secret, che Google
   rilascia pure ai client "Desktop", sta nel portachiavi insieme al refresh token (confermato
   dal maintainer il 2026-11-20): la persona lo fornisce una volta, mai come argomento di riga
   di comando. L'id del client OAuth sta nel profilo; nessun id o segreto di client è
   distribuito con il codice.
8. **Il canale stdio è riservato al protocollo.** In modalità server lo standard output porta solo
   messaggi MCP; log e diagnostica vanno sullo standard error. Il server non apre mai il browser:
   se la sessione Google manca o è revocata, gli strumenti rispondono con un errore che indica
   di rieseguire il login.

## Alternative considerate

- **Skill che insegna a Claude a usare la CLI**: scartata come soluzione, vale solo dove c'è una
  shell (Claude Code) e non dà strumenti tipizzati. Resta utile come esperimento.
- **Server MCP remoto (HTTP) con autenticazione per utente**: rimandata. Serve solo quando lo
  usano più persone o serve da claude.ai e da mobile, e porta hosting, OAuth lato server e
  gestione delle sessioni.
- **Pacchetto separato `pynteracta-mcp`**: scartata per ora. Il server è sottile e segue passo
  passo la libreria; un extra opzionale tiene leggera l'installazione base senza un secondo
  ciclo di rilascio.
- **Identità service account come identità prevista del server**: scartata, per l'ampiezza dei
  permessi (vedi Contesto, punto 2). Resta possibile, con avviso.
- **Rifiutare all'avvio i profili con service account**: scartata dal maintainer. Il server li
  accetta con un avviso, così resta usabile dove l'identità personale non c'è (automazioni,
  prove).
- **Token Google statico in variabile d'ambiente**: scartata. Scade in un'ora e finirebbe nel
  file di configurazione del client MCP.
- **Comando esterno che restituisce il token (per esempio `gcloud auth print-access-token`)**:
  scartata come soluzione principale. Richiede uno strumento estraneo su ogni postazione e non è
  certo che il token porti lo scope accettato dal tenant. Resta possibile da libreria con
  `google_token_provider`.
- **Refresh token in un file `0o600`, come la cache del token**: scartata. È un segreto di lunga
  durata e su Windows, dove gira gran parte dei client MCP desktop, i permessi stretti sui file
  non sono garantiti (RNF-002 lo riconosce già).
- **Esporre tutte le scritture, o i task sempre attivi**: scartata. Un agente che legge contenuti
  non fidati e ha strumenti di scrittura è il rischio principale; si parte dal gruppo più
  piccolo e lo si accende di proposito.

## Conseguenze

- `specs/prd.md`:
  - §1: il server MCP non è più un uso futuro ma una parte del pacchetto.
  - §2: nuovo attore (client MCP o agente LLM che agisce per conto della persona); la riga
    "Utente Google" non dice più solo "fornisce un access token".
  - §3: RF-002 e RF-003 precisati (login integrato, rinnovo, durata di un'ora del token
    Interacta); in RF-002 lo scope minimo passa da `profile` a `email`; nuovi RF-026 (login
    Google integrato) e RF-027 (server MCP locale), da realizzare: le spec 10 e 11 li precisano
    e aggiungono i sottorequisiti.
  - §4: RNF-001 esteso a refresh token, authorization code, verificatore PKCE, id token e client
    secret; nuovo RNF-012 (segreti di lunga durata nel portachiavi), che affianca RNF-002; nuovo
    RNF-013 (canale stdio). RNF-004 non cambia: il client resta sincrono.
  - §5: la riga "Google OAuth2" descrive gli endpoint di autorizzazione e di token di Google,
    che la libreria ora chiama direttamente; nuove righe per il client MCP e per il portachiavi.
  - §6: refresh token e client secret sono nuovi dati scritti dalla libreria (nel portachiavi).
    I dati letti dal tenant passano al client MCP e da lì al fornitore del modello: è un
    trattamento che la libreria non controlla, a carico di chi abilita il server, e va detto.
  - §7: esce "ottenere un token Google per conto dell'utente"; entrano il server MCP remoto, le
    scritture via MCP oltre i task e l'area admin via MCP.
- `CLAUDE.md`, con questo ADR: la regola non negoziabile sui token cita i segreti del login
  Google; nuove regole sul portachiavi e sul canale stdio; la regola sui segreti fuori dal
  repository cita il client OAuth; la regola sulle operazioni ripetute vale anche per il server;
  l'introduzione cita le due funzioni decise. La mappa dei moduli e lo "Stack" li aggiornano le
  spec 10 e 11, quando i moduli e le dipendenze opzionali esistono.
- `ROADMAP.md`: due righe ⏳, una per il login (M36) e una per il server (M37), all'apertura
  delle spec 10 e 11.
- Codice: nessuna modifica con questo ADR.
- `docs/` e `README.md`: `authentication.md` oggi afferma che la libreria non esegue il login
  Google e va riscritta in quella parte; servono una guida al server MCP (installazione,
  configurazione del client, flag delle scritture, avvertenze) e l'aggiornamento della home e
  del README, che descrivono lo scope.
- Dipendenze nuove, entrambe opzionali: l'SDK MCP per Python e `keyring`. L'SDK è asincrono: le
  chiamate sincrone della libreria girano fuori dal ciclo degli eventi, senza
  `AsyncInteractaClient`.
- Fuori dal progetto: serve un client OAuth di tipo "Desktop" in un progetto Google Cloud
  dell'ente, con l'app dichiarata "Internal" nel Workspace (niente verifica di Google, solo
  account dell'ente).
- Con un profilo service account il perimetro degli strumenti non cambia (niente area admin,
  scritture solo sui task e solo con il flag), ma letture e scritture avvengono con i permessi
  dell'identità tecnica, più larghi di quelli di una persona: la guida lo dice e sconsiglia di
  unire service account e `--enable-task-writes` senza una ragione.
- Limiti da dichiarare, non risolvibili dal server: la conferma di un'eliminazione dipende dal
  client MCP, perché le annotazioni sono un'indicazione e non un obbligo; il server non può
  impedire al modello di seguire istruzioni contenute in un post, può solo ridurre ciò che il
  modello è in grado di fare.
- Diventa più facile: usare Interacta in linguaggio naturale con i propri permessi, e usare la
  CLI con l'identità personale senza procurarsi un token ogni ora. Diventa più difficile: la
  libreria custodisce un segreto di lunga durata, la superficie pubblica cresce di un comando e
  di un protocollo, e i test devono coprire un flusso OAuth e un server senza toccare la rete.

## Verifiche fatte prima di accettare

Eseguite il 2026-11-20; passaggi ed esiti sono in
[`../bozze/verifiche-adr-0002.md`](../bozze/verifiche-adr-0002.md).

1. **Sul tenant**: il token Interacta ottenuto dallo scambio dura un'ora. Lo scambio accetta un
   token Google con lo scope `email`; con il solo `profile` risponde `401` `BAD_CREDENTIALS`. Il
   tenant accetta i token emessi dal client "Desktop" dell'ente, in un'app "Internal".
2. **Sulla console Google**: il client "Desktop" richiede il client secret allo scambio del
   codice (senza: `invalid_request`, "client_secret is missing."), e la risposta contiene il
   refresh token. La decisione 7 resta com'è.
