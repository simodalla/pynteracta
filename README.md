PYNTeractA, client ed utility per api rest di Interacta
-------------------------------------------------------

Utility e libreria wrapper open-source in linguaggio Python per l'interfacciamento con le api rest
di [Interacta](https://catalogocloud.agid.gov.it/service/1892).


Installazione
-------------

```
python -m pip install pynteracta
```

Utilizzo utility command line
-----------------------------

Pynteracta ha un'interfaccia a riga di comando per verificare l'accesso ad un ambiente di produzione di Interacta.

E' supportato lo schema di autenticazione Server-to-Serveril per mezzo di Service Account: ```

- [Service Account](https://injenia.atlassian.net/wiki/spaces/IEAD/pages/3624075265/Autenticazione#Autenticazione-via-Service-Account-(Server-to-Server))
```

Lista dei primi 10 post della community identificata dall'id passata come parametro

    $ pynta --env **TOML_ENV_FILE** get-community-definition
```

Lista dei primi 10 post della community identificata dall'id passata come parametro

    $ pynta -e **PATH_CONF_TOML**  list-posts **COMMUNITY-ID**
