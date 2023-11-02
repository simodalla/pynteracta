from pathlib import Path

import rich
import typer
from devtools import debug
from rich.table import Table
from rich.text import Text

from ..api import InteractaApi
from .users import app as users_app
from .utils import cli_init_setting, table_list_posts

app = typer.Typer(help="")
app.add_typer(users_app, name="users")

state = {"env_file": None}


@app.callback()
def set_env_file(
    env_file: Path = typer.Option(  # noqa: B008
        Path("~/.pynta.toml"), "--env", "-e", help="Environment file in formato toml"
    ),
):
    state["env_file"] = env_file


@app.command()
def get_community_definition(  # noqa: C901
    community_id: int = typer.Option(0, "--id", "-i"),
    community_name: str = typer.Option("", "--name", "-n"),
    fields_definition: bool = typer.Option(False, "--fields", "-fd"),
    workflow_definition: bool = typer.Option(False, "--workflow", "-wf"),
    output_table: bool = typer.Option(False, "--table", "-t"),
):
    """
    Mostra la definizione del post di una community e le relative impostazioni, dati workflow,
    campi custom ecc
    """
    if not community_id and not community_name:
        rich.print(
            "[bold red]Errore: inserisci almeno uno tra i due argomenti 'community_id' e"
            " 'community_name' [/bold red]"
        )
        raise typer.Exit(code=1)

    settings = cli_init_setting(env_file=state["env_file"]).interacta
    api = InteractaApi(settings=settings)
    api.login()

    if not community_id and community_name:
        if community_name not in settings.model_dump():
            rich.print(
                f"[bold red]Errore: non è presente alcuna configurazione per la community"
                f" '{community_name}'[/bold red]"
            )
            raise typer.Exit(code=1)
        community_id = settings.model_dump()[community_name]["community_id"]

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

    if workflow_definition:
        if output_table:
            state_table = Table(
                "Id",
                "Nome",
                "Iniziale",
                "Finale",
                "Metadati",
                title=f"Stati di {community_title}",
                show_lines=True,
            )
            for state_data in post_definition.workflow_definition.states:
                if state_data.deleted:
                    continue

                state_color = (
                    state_data.metadata["style_color"]
                    if "style_color" in state_data.metadata
                    else ""
                )
                state_table.add_row(
                    str(state_data.id),
                    Text(state_data.name, style=f"bold {state_color}"),
                    str(state_data.init_state),
                    str(state_data.terminal),
                    str(state_data.metadata),
                )
            rich.print(state_table)
            transitions_table = Table(
                "Id",
                "Nome",
                "Trasizione",
                "Screen",
                title=f"Transizine di {community_title}",
                show_lines=True,
            )
            for transition in post_definition.workflow_definition.transitions:
                state_from_color = (
                    transition.from_state.metadata["style_color"]
                    if "style_color" in transition.from_state.metadata
                    else ""
                )
                state_to_color = (
                    transition.to_state.metadata["style_color"]
                    if "style_color" in transition.to_state.metadata
                    else ""
                )
                transition_txt = Text(transition.from_state.name, style=f"bold {state_from_color}")
                transition_txt.append(" --> ", style=f"bold {state_to_color}")
                transition_txt.append(transition.to_state.name, style=f"bold {state_to_color}")

                transitions_table.add_row(
                    str(transition.id), transition.name, transition_txt, str(transition.screen)
                )
            rich.print(transitions_table)
        else:
            rich.print_json(post_definition.workflow_definition.model_dump_json())
        raise typer.Exit()

    rich.print_json(post_definition.model_dump_json())


@app.command()
def list_posts(
    community: int = typer.Argument(..., help="Id della community"),
):
    """
    Lista dei post presenti in una community.
    """
    settings = cli_init_setting(env_file=state["env_file"]).interacta
    api = InteractaApi(settings=settings)
    api.login()

    posts = api.list_posts(community_id=community).items
    rich.print(table_list_posts(posts=posts, settings=api.settings))


@app.command()
def echo_settings():
    """
    Mostra gli environment
    """
    debug(cli_init_setting(env_file=state["env_file"]).model_dump())
