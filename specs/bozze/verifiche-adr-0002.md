# Verifiche prima di accettare l'ADR 0002

Le due verifiche di fatto elencate nei "Punti aperti" della
[bozza dell'ADR 0002](adr-0002-server-mcp-login-google.md): il client secret sulla console Google
e, sul tenant, lo scope accettato e la durata del token Interacta. Si fanno insieme: si crea il
client OAuth, si prova lo scambio del codice con e senza client secret, poi si usa il token
ottenuto contro il tenant.

Stato: procedura scritta il 2026-11-20 e **non ancora provata**. I nomi delle voci della console
Google possono differire leggermente. I comandi sono per il Terminale di macOS; su Windows si
usano Git Bash o WSL.

I token che compaiono a terminale sono credenziali vere: non vanno incollati in chat, in issue
né in file del repository. In questo documento vanno riportati solo gli esiti.

## 1. Creare il client OAuth nella console Google

1. Aprire la console Google Cloud sul progetto dell'ente, sezione "Google Auth Platform" (prima
   "Schermata di consenso OAuth").
2. In "Pubblico" impostare il tipo di utente su **Interno**.
3. In "Accesso ai dati" aggiungere lo scope `.../auth/userinfo.profile`.
4. In "Client" creare un client di tipo **App desktop** e annotare ID client e client secret.

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

```bash
export PYNTERACTA_GOOGLE_OAUTH2_TOKEN="<access_token>"
```

```bash
pynteracta --base-url https://<tenant> auth login --google --profile prova-google
```

- **`✓ Authenticated as: <nome>`**: lo scope `profile` basta e il tenant accetta i token del
  client dell'ente.
- **Errore di autenticazione**: ripetere il passo 2 con `scope=openid%20email%20profile` e
  riprovare. Se fallisce ancora, è probabile che il tenant accetti solo i token di client
  specifici, e va chiesto al fornitore.

## 4. Misurare la durata del token Interacta

```bash
pynteracta --base-url https://<tenant> --profile prova-google --token-cache memory --log-level INFO auth whoami
```

Nei log compare la riga `auth.token_obtained` con `expires_at`: la differenza con l'ora corrente
(in UTC) è la durata.

## Esiti

Da compilare dopo le prove; sono i dati che l'ADR e la spec 10 devono citare.

| Verifica | Esito | Data |
|---|---|---|
| Il client "Desktop" richiede il client secret allo scambio del codice | | |
| La risposta di Google contiene il `refresh_token` | | |
| Scope con cui lo scambio con Interacta riesce | | |
| Il tenant accetta i token emessi dal client dell'ente | | |
| Durata del token Interacta dopo lo scambio | | |
