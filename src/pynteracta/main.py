from pathlib import Path

import rich
import typer
from devtools import debug
from rich.table import Table

from pynteracta import cli
from pynteracta.exceptions import InteractaError
from pynteracta.settings import AppSettings

app = typer.Typer(help="")
state = {"env_file": ""}


@app.callback()
def main(env_file: Path = typer.Option("env.toml", "--env", "-e")):  # noqa: B008
    state["env_file"] = env_file


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
        api.login()
    except InteractaError as e:
        rich.print(f"[bold red]Autenticazione fallita![/bold red] --> [red]{e}[/red]")
        typer.Exit(code=1)
    rich.print("[green]Login effettuato con successo![/green]")
    rich.print("[cyan]Elenco dei post:[/cyan]")
    rich.print(api.table_list_posts(posts=api.get_posts()))


@app.command()
def list_posts(
    community: int = typer.Argument(1, help="Id della community"),
):
    """
    Mostra la lista dei post presenti in una community.
    """
    settings = AppSettings(_env_file=state["env_file"])
    api = cli.CliInteractaApi(settings=settings.interacta)
    api.login()

    posts = api.list_posts(community_id=community).items
    rich.print(api.table_list_posts(posts=posts))


@app.command()
def get_community_definition(
    community_id: int = typer.Option(0, "--id", "-i"),
    community_name: str = typer.Option("", "--name", "-n"),
    fields_definition: bool = typer.Option(False, "--fields", "-fd"),
    output_table: bool = typer.Option(False, "--table", "-t"),
):
    if not community_id and not community_name:
        rich.print(
            "[bold red]Errore: inserisci almeno uno tra i due argomenti 'community_id' e"
            " 'community_name' [/bold red]"
        )
        raise typer.Exit(code=1)

    settings = AppSettings(_env_file=state["env_file"])
    api = cli.CliInteractaApi(settings=settings.interacta)
    api.login()

    if not community_id and community_name:
        if community_name not in settings.interacta.model_dump():
            rich.print(
                f"[bold red]Errore: non è presente alcuna configurazione per la community"
                f" '{community_name}'[/bold red]"
            )
            raise typer.Exit(code=1)
        community_id = settings.interacta.model_dump()[community_name]["community_id"]

    community = api.get_community_detail(community_id=community_id)
    community_name = community.community.name
    community_title = f"Community --> [cyan]{community_name}[/cyan]"
    post_definition = api.get_post_definition_detail(community_id=community_id)

    if fields_definition:
        if output_table:
            table = Table(
                "Id", "Label", "Type", "Enum Values", title=community_title, show_lines=True
            )
            for field in post_definition.field_definitions:
                table.add_row(
                    str(field.id),
                    field.label,
                    field.type.name,
                    ",".join([str((d.id, d.label)) for d in field.enum_values]),
                )
            rich.print(table)
        else:
            rich.print(f"{community_title}\n")
            for field in post_definition.field_definitions:
                rich.print(field)
        raise typer.Exit()

    rich.print_json(post_definition.model_dump_json())


@app.command()
def echo_settings():
    settings = AppSettings(_env_file=state["env_file"])
    debug(settings.model_dump(exclude={"interacta": {"service_account": {"private_key"}}}))
