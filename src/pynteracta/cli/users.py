from enum import StrEnum
from pathlib import Path

import rich
import typer
from pydantic import RootModel
from rich.progress import Progress
from rich.table import Table

from ..enums import LoginProviderEnum
from ..schemas.models import ListSystemUsersElement
from ..schemas.requests import ListSystemUsersIn
from ..utils.models import UsersStats
from .utils import cli_init_api, user_login_info

app = typer.Typer()

state = {"env_file": None}


class OutputFormat(StrEnum):
    TABLE = "table"
    JSON = "json"


@app.callback()
def set_env_file(
    env_file: Path = typer.Option(  # noqa: B008
        Path("~/.pynta.toml"), "--env", "-e", help="Environment file in formato toml"
    ),
):
    state["env_file"] = env_file


@app.command("list")
def list_users(  # noqa: C901
    show_not_active: bool = typer.Option(False, help="Mostra anche gli utenti non attivi"),
    login_provider: list[LoginProviderEnum] = typer.Option(  # noqa: B008
        [], "--login-provider", "-lp", help="Filtra gli utenti con i login provider selezionati"
    ),
    show_no_login_provider: bool = typer.Option(
        False, help="Mostra solo gli utenti senza alcun login provider"
    ),
    user_filter: str = typer.Option(
        "",
        "--user-filter",
        "-uf",
        help="Filtra gli utenti con una ricerca fulltext su nome cognome e email",
    ),
    divergent_contact_email: bool = typer.Option(
        False,
        help="Mostra solo gli utenti che hanno email di contatto diverse da quelle"
        " del login provider",
    ),
    output_format: OutputFormat = typer.Option(  # noqa: B008
        OutputFormat.TABLE, "--out-format", "-of", help="Tipo di formato dell'output"
    ),
):
    filter_data = ListSystemUsersIn()
    if not show_not_active:
        filter_data.status_filter = [0]
    if login_provider:
        filter_data.login_provider_filter = list(login_provider)
    if show_no_login_provider:
        filter_data.login_provider_filter = []
    if user_filter:
        filter_data.full_text_filter = user_filter

    api, _ = cli_init_api(env_file=state["env_file"])
    with Progress() as progress:
        task = progress.add_task("Get data from Interacta...", total=None)
        users = api.all_users(data=filter_data)
        progress.remove_task(task)

    users_stats = UsersStats.create_by_user_list(users=users)

    if show_no_login_provider:
        users = users_stats.no_provider.values() if users_stats.no_provider else []

    if not users:
        rich.print("[red]Nessun risultato corrispondente ai parametri.[/red]")
        raise typer.Exit(2)

    if output_format == OutputFormat.TABLE:
        table = Table(
            "Cognome",
            "Nome",
            "Contatto Email",
            "Login Info",
            "Stato",
            show_lines=True,
        )
        for user in users:
            login_info = user_login_info(user=user)
            if divergent_contact_email and not login_info.startswith("[red]"):
                continue

            table.add_row(
                user.last_name,
                user.first_name,
                user.contact_email,
                login_info,
                "[green]attivo[/green]"
                if user.id in users_stats.active
                else "[red]non attivo[/red]",
            )

        if table.row_count == 0:
            rich.print("[red]Nessun risultato corrispondente ai parametri.[/red]")
            raise typer.Exit(3)

        rich.print(table)
        table_summary = Table("Dato", "Conteggio", show_header=False, title="Conteggi")
        for k, v in users_stats.counts.items():
            table_summary.add_row(str(k), str(v))
        rich.print(table_summary)
        raise typer.Exit(0)

    rich.print_json(RootModel[list[ListSystemUsersElement]](users).model_dump_json())
