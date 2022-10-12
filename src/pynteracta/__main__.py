"""Pynteracta

Usage:
------

    $ pynteracta

Contact:
--------

- https://www.unionerenolavinosamoggia.bo.it/index.php/contatti

More information is available at:

- https://github.com/simodalla/pynteracta


Version:
--------

- pynteracta v0.1.2
"""

import os

import rich
import typer
from rich.prompt import Prompt

from pynteracta import cli, utils
from pynteracta.exceptions import InteractaLoginError

app = typer.Typer()


@app.command()
def playground():
    rich.print("[cyan]Connessione al Playground di interacta...[cyan]")
    api = cli.CliPlaygroundApi()
    try:
        token = api.bootstrap_token()
        rich.print(token)
    except InteractaLoginError as e:
        rich.print(f"[bold red]Autenticazione fallita![/bold red] --> [red]{e}[/red]")
        typer.Exit(code=1)
    rich.print("[green]ogin effettuato con successo![/green]")
    rich.print("[cyan]Elenco dei post:[/cyan]")
    rich.print(api.table_list_posts(posts=api.get_list_community_posts()))


@app.command()
def login(service_account_file: str = "", user: str = "", base_url: str = ""):
    """
    Effettua il login .

    If --formal is used, say hi very formally.
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
    utils.clean_session_access_token()
    rich.print("[green]Logout effettuato con successo![/green]")


@app.command()
def list_posts(
    community: int = 1,
    base_url: str = "",
):
    base_url = base_url if base_url else os.getenv("INTERACTA_BASEURL", "")
    if not base_url:
        base_url = Prompt.ask("Interacta url")
    api = cli.CliInteractaApi(base_url=base_url)
    api.access_token = utils.get_session_access_token()
    if not api.access_token:
        rich.print("[bold red]Sembra ci sia un problema. Effettua il login![/bold red]")
        typer.Exit(code=1)
    rich.print(api.table_list_posts(api.get_list_community_posts(community_id=community)))


if __name__ == "__main__":
    app()
