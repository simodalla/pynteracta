import os

import rich
import typer
from rich.prompt import Prompt

from pynteracta import cli, utils
from pynteracta.exceptions import InteractaLoginError

app = typer.Typer(help="")

help_text_base_url = (
    "URL di base ambiente di produzione. Se non valorizzato viene impostato dalla variabile "
    "di ambiente INTERACTA_BASEURL o richiesta in input."
)
help_text_user = (
    "Username per autenticazione username/password. Questo argomento viene"
    " ignorato se è stato valorizzata l'opzione service_account_file."
)


@app.command()
def playground():
    """
    Effettua il login e mostra la lista dei post presenti nell'ambiente demo Playgroud.

    Leggi la documentazione -->
    https://injenia.atlassian.net/wiki/spaces/IEAD/pages/3641081900/Playground
    """
    rich.print("[cyan]Connessione all'ambiente Playground di Interacta...[cyan]")
    api = cli.CliPlaygroundApi()
    try:
        api.bootstrap_token()
    except InteractaLoginError as e:
        rich.print(f"[bold red]Autenticazione fallita![/bold red] --> [red]{e}[/red]")
        typer.Exit(code=1)
    rich.print("[green]Login effettuato con successo![/green]")
    rich.print("[cyan]Elenco dei post:[/cyan]")
    rich.print(api.table_list_posts(posts=api.get_list_community_posts()))


@app.command()
def login(
    service_account_file: str = typer.Option(
        "", help="Path del file json per autenticazione con Service Account."
    ),
    user: str = typer.Option("", help=help_text_user),
    base_url: str = typer.Option("", help=help_text_base_url),
):
    """
    Effettua il login nell'ambiente di produzione.

    Se viene passato l'argomento service_account_file il login viene tentato con le credenziali del
    service account ignorando l'autenticazione username/password.

    Specifica la URL di base dell'ambiente di produzione.
    """
    method_prepare_type = None
    auth_type = ""
    params = {}
    user = user if user else os.getenv("INTERACTA_USERNAME", "")

    if service_account_file:
        method_prepare_type = "prepare_service_login_from_file"
        auth_type = "service account"
        params = {"file_path": service_account_file}
    else:
        method_prepare_type = "prepare_credentials_login"
        auth_type = "username/password"
        user = user if user else os.getenv("INTERACTA_USERNAME", "")
        password = os.getenv("INTERACTA_PASSWORD", "")
        if not user:
            user = Prompt.ask("Username")
        if not password:
            password = Prompt.ask("Password", password=True)
        params = {"username": user, "password": password}
    base_url = base_url if base_url else os.getenv("INTERACTA_BASEURL", "")
    if not base_url:
        base_url = Prompt.ask("Interacta url")

    rich.print(f"[cyan]Connessione all'instanza Interacta {base_url} con '{auth_type}' ...[cyan]")
    api = cli.CliInteractaApi(base_url=base_url)
    try:
        method = getattr(api, method_prepare_type)
        url, data = method(**params)
        access_token = api.login(url, data)
        utils.set_session_access_token(access_token)
    except InteractaLoginError as e:
        rich.print(f"[bold red]Autenticazione fallita![/bold red] --> [red]{e}[/red]")
        typer.Exit(code=1)
    rich.print("[green]Login effettuato con successo![/green]")


@app.command()
def logout():
    """Effettua il logout dall'ambiente di produzione."""
    utils.clean_session_access_token()
    rich.print("[green]Logout effettuato con successo![/green]")


@app.command()
def list_posts(
    community: int = typer.Argument(1, help="Id della community"),
    base_url: str = typer.Option("", help=help_text_base_url),
):
    """
    Mostra la lista dei post presenti in una community.

    Specifica la URL di base dell'ambiente di produzione.
    """
    base_url = base_url if base_url else os.getenv("INTERACTA_BASEURL", "")
    if not base_url:
        base_url = Prompt.ask("Interacta url")
    api = cli.CliInteractaApi(base_url=base_url)
    api.access_token = utils.get_session_access_token()
    if not api.access_token:
        rich.print("[bold red]Sembra ci sia un problema. Effettua il login![/bold red]")
        typer.Exit(code=1)
    rich.print(api.table_list_posts(api.get_list_community_posts(community_id=community)))
