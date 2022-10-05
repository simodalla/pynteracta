import getpass
import os

import typer
from rich import print
from rich.prompt import Prompt

from pynteracta import cli, utils
from pynteracta.exceptions import InteractaLoginError

app = typer.Typer()


@app.command()
def playground():
    print("[cyan]Connessione al Playground di interacta...[cyan]")
    api = cli.CliPlaygroundApi()
    try:
        token = api.bootstrap_token()
        print(token)
    except InteractaLoginError as e:
        print(f"[bold red]Autenticazione fallita![/bold red] --> [red]{e}[/red]")
        return False
    print("[green]ogin effettuato con successo![/green]")
    print("[cyan]Elenco dei post:[/cyan]")
    print(api.table_list_posts(posts=api.get_list_community_posts()))


@app.command()
def login_creds(
    base_url: str = typer.Argument("", envvar="INTERACTA_BASEURL"),
    user: str = "",
    password: str = "",
):
    user = user if user else os.getenv("INTERACTA_USERNAME", "")
    password = password if password else os.getenv("INTERACTA_PASSWORD", "")
    if not user:
        user = Prompt.ask("Username")
    if not password:
        password = Prompt.ask("Password", password=True)
    print(f"[cyan]Connessione all'instanza Intercta {base_url} ...[cyan]")
    api = cli.CliInteractaApi(base_url=base_url)
    url, data = api.prepare_credentials_login(username=user, password=password)
    try:
        access_token = api.login(url, data)
        utils.set_session_access_token(access_token)
    except InteractaLoginError as e:
        print(f"[bold red]Autenticazione fallita![/bold red] --> [red]{e}[/red]")
        return 1
    print("[green]Login effettuato con successo![/green]")


@app.command()
def logout():
    utils.clean_session_access_token()
    print("[green]Logout effettuato con successo![/green]")


@app.command()
def list_posts(
    base_url: str = typer.Argument("", envvar="INTERACTA_BASEURL"),
    community: int = 1,
):
    api = cli.CliInteractaApi(base_url=base_url)
    api.access_token = utils.get_session_access_token()
    if not api.access_token:
        print("[bold red]Sembra ci sia un problema. Effettua il login![/bold red]")
        return 2
    print(api.table_list_posts(api.get_list_community_posts(community_id=community)))


@app.command()
def auth_service(
    base_url: str = typer.Argument("aaa", envvar="INTERACTA_BASEURL"),
    auth_key: str = typer.Argument("", envvar="INTERACTA_SERVICE_AUTH_KEY"),
):
    # print(endpoint, auth_key)
    pass


if __name__ == "__main__":
    app()
