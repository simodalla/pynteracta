# Verifiche prima di accettare l'ADR 0002

Le due verifiche di fatto elencate nei "Punti aperti" della
[bozza dell'ADR 0002](adr-0002-server-mcp-login-google.md): il client secret sulla console Google
e, sul tenant, lo scope accettato e la durata del token Interacta. Si fanno insieme: si crea il
client OAuth, si prova lo scambio del codice con e senza client secret, poi si usa il token
ottenuto contro il tenant.

Stato: procedura scritta ed **eseguita il 2026-11-20** sul tenant dell'ente; gli esiti sono in
fondo. Lo scope `profile` del passo 2 non è bastato: il tenant vuole `email`, trovato ripetendo
il passo 2 prima con `scope=openid%20email%20profile` e poi con `scope=email`. I comandi qui
sotto restano quelli della prima esecuzione, con `profile`. I nomi delle voci della console Google possono differire
leggermente. I comandi sono per il Terminale di macOS; su Windows si usano Git Bash o WSL.

I token che compaiono a terminale sono credenziali vere: non vanno incollati in chat, in issue
né in file del repository. In questo documento vanno riportati solo gli esiti.

## 1. Creare il client OAuth nella console Google

Il "progetto dell'ente" è un progetto Google Cloud che appartiene all'organizzazione del Google
Workspace dell'ente (non un progetto personale, né "Nessuna organizzazione"): solo così il tipo
di utente "Interno" è selezionabile. Serve un account dell'ente con il ruolo di Proprietario o
Editor sul progetto, o il permesso di crearne uno.

1. Andare su <https://console.cloud.google.com> ed entrare con l'account dell'ente.
2. Aprire il selettore dei progetti, in alto a sinistra accanto al logo "Google Cloud". Nella
   finestra controllare che in alto sia selezionata l'organizzazione dell'ente (il dominio del
   Workspace).
3. Scegliere un progetto esistente adatto, oppure "Nuovo progetto": dare un nome (per esempio
   `pynteracta-login`), verificare che "Organizzazione" sia il dominio dell'ente e premere
   "Crea". Poi selezionarlo dal selettore.
4. Dal menu ☰ aprire "API e servizi" → "Schermata consenso OAuth": si apre "Google Auth
   Platform". Indirizzo diretto: <https://console.cloud.google.com/auth/overview>.
5. Se la piattaforma non è ancora configurata, premere "Inizia" e completare la procedura:
   nome dell'app, email di assistenza, pubblico **Interno**, email di contatto, accettazione
   delle norme sui dati utente. Se è già configurata, controllare in "Pubblico" che il tipo di
   utente sia **Interno**.
6. In "Accesso ai dati" premere "Aggiungi o rimuovi ambiti", selezionare
   `.../auth/userinfo.profile` e salvare.
7. In "Client" premere "Crea client", tipo di applicazione **App desktop**, dare un nome e
   creare. Annotare l'ID client e il client secret dalla finestra che compare: il secret può
   non essere più visibile dopo la chiusura, quindi va copiato subito in un gestore di password
   (mai nel repository).

Se "Interno" non è selezionabile, il progetto non è sotto l'organizzazione dell'ente: va creato
o spostato lì, oppure chiesto all'amministratore del Workspace.

## 2. Verificare se il client secret è richiesto

Impostare l'ID del client:

```bash
CLIENT_ID="<id-del-client>.apps.googleusercontent.com"
```

Inserire il secret senza che resti nella cronologia della shell:

```bash
read -s CLIENT_SECRET
```

Generare il verificatore PKCE:

```bash
VERIFIER=$(openssl rand -hex 32)
```

Calcolare la challenge:

```bash
CHALLENGE=$(printf '%s' "$VERIFIER" | openssl dgst -sha256 -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')
```

Stampare l'indirizzo di autorizzazione e aprirlo nel browser:

```bash
echo "https://accounts.google.com/o/oauth2/v2/auth?client_id=$CLIENT_ID&redirect_uri=http://127.0.0.1:8765&response_type=code&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.profile&code_challenge=$CHALLENGE&code_challenge_method=S256&access_type=offline&prompt=consent"
```

Dopo il consenso il browser mostra un errore di connessione: è atteso, perché nessuno ascolta su
quella porta. Dalla barra degli indirizzi copiare il valore tra `code=` e `&`, sostituendo ogni
`%2F` con `/`:

```bash
CODE="<codice-copiato>"
```

Provare lo scambio **senza** secret:

```bash
curl -s https://oauth2.googleapis.com/token \
  --data-urlencode "code=$CODE" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "redirect_uri=http://127.0.0.1:8765" \
  --data-urlencode "code_verifier=$VERIFIER" \
  --data-urlencode "grant_type=authorization_code"
```

Poi **con** il secret:

```bash
curl -s https://oauth2.googleapis.com/token \
  --data-urlencode "code=$CODE" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "redirect_uri=http://127.0.0.1:8765" \
  --data-urlencode "code_verifier=$VERIFIER" \
  --data-urlencode "grant_type=authorization_code"
```

Come leggere l'esito:

- **Senza secret errore, con secret token**: il secret è richiesto e la decisione 7 dell'ADR
  resta com'è.
- **Token già senza secret**: il secret non serve e la parte della decisione 7 che lo riguarda
  cade.
- **`invalid_grant` al secondo tentativo**: il codice è stato consumato dal primo. Riaprire
  l'indirizzo, prendere un codice nuovo e provare solo con il secret.

La risposta buona deve contenere `access_token` e `refresh_token`. Se il `refresh_token` manca,
il login integrato non può rinnovare la sessione: va capito perché prima di procedere.

## 3. Verificare lo scope sul tenant

Si usa l'`access_token` appena ottenuto, che porta il solo scope `profile` ed è emesso dal
client dell'ente. Se c'è un tenant di certificazione, la prova si fa lì.

Creare prima il profilo di prova con l'indirizzo del tenant. Va fatto **prima** del login: nelle
versioni di `pynteracta` senza la correzione del branch `bugfix_login_profilo_nuovo`,
`auth login --profile` su un profilo che non esiste scrive in `config.toml` una voce senza
`base_url`, e da quel momento ogni comando fallisce con un `ValidationError`, anche sugli altri
profili (se capita, si rimedia togliendo a mano la sezione `[profiles.prova-google]`). Con la
correzione il login salva da sé l'indirizzo, e questa sequenza resta comunque valida.

```bash
pynteracta config add-profile prova-google --base-url https://<tenant>
```

Inserire l'`access_token` senza che resti nella cronologia della shell (incollarlo e premere
Invio):

```bash
read -s PYNTERACTA_GOOGLE_OAUTH2_TOKEN
```

```bash
export PYNTERACTA_GOOGLE_OAUTH2_TOKEN
```

```bash
pynteracta --profile prova-google auth login --google --profile prova-google
```

- **`✓ Authenticated as: <nome>`**: lo scope `profile` basta e il tenant accetta i token del
  client dell'ente.
- **Errore di autenticazione**: ripetere il passo 2 con `scope=openid%20email%20profile` e
  riprovare. Se fallisce ancora, provare con un token dello stesso scope preso dall'OAuth2
  Playground di Google (vedi `docs/authentication.md`): se quello funziona, il tenant accetta
  solo i token di client specifici, e va chiesto al fornitore.

## 4. Misurare la durata del token Interacta

La riga `auth.token_obtained` con `expires_at` (in UTC) compare già nell'output del login del
passo 3. Per rileggerla, entro l'ora di vita del token Google:

```bash
pynteracta --profile prova-google --token-cache memory --log-level INFO auth whoami
```

La durata è la differenza tra `expires_at` e `timestamp` della stessa riga.

## 5. Pulizia

```bash
pynteracta config remove-profile prova-google
```

```bash
unset PYNTERACTA_GOOGLE_OAUTH2_TOKEN CLIENT_SECRET CODE VERIFIER
```

## Esiti

Da compilare dopo le prove; sono i dati che l'ADR e la spec 10 devono citare.

| Verifica | Esito | Data |
|---|---|---|
| Il client "Desktop" richiede il client secret allo scambio del codice | Sì. Senza secret: `invalid_request`, "client_secret is missing."; con il secret lo stesso codice dà il token | 2026-11-20 |
| La risposta di Google contiene il `refresh_token` | Sì, insieme all'`access_token` (scope concesso: `profile`, `userinfo.profile`) | 2026-11-20 |
| Scope con cui lo scambio con Interacta riesce | `email` (minimo; Google concede `email`, `userinfo.email` e `openid`). Riesce anche con `openid email profile`. Con il solo `profile` il tenant risponde `401` `BAD_CREDENTIALS`, anche se Google dà il token per valido | 2026-11-20 |
| Il tenant accetta i token emessi dal client dell'ente | Sì, sul tenant di produzione, con un client "App desktop" di un progetto interno all'organizzazione | 2026-11-20 |
| Durata del token Interacta dopo lo scambio | Un'ora (`expires_at` 23:27:19Z, ottenuto alle 22:27:20Z) | 2026-11-20 |
