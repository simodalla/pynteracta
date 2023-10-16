from pathlib import Path

import rich
import typer
from rich.table import Table

from ..api import InteractaApi
from ..enums import LoginProviderEnum
from ..exceptions import InteractaError
from ..schemas.models import BaseListPostsElement, ListSystemUsersElement
from ..settings import AppSettings, InteractaSettings, init_app_settings


def cli_init_setting(env_file: Path | None = None) -> AppSettings:
    try:
        return init_app_settings(env_file=env_file)
    except InteractaError as ie:
        rich.print(f"[bold red]{ie}[/bold red]")
        raise typer.Exit(code=10) from ie


def cli_init_api(env_file: Path | None = None) -> tuple[InteractaApi, AppSettings]:
    settings = cli_init_setting(env_file=env_file)
    try:
        api = InteractaApi(settings=settings.interacta)
        api.login()
        return api, settings
    except InteractaError as ie:
        rich.print(f"[bold red]{ie}[/bold red]")
        raise typer.Exit(code=10) from ie


def table_list_posts(posts: list[BaseListPostsElement], settings: InteractaSettings) -> Table:
    table = Table("Id", "Titolo", "Descrizione", show_lines=True)
    for post in posts:
        table.add_row(
            f"[link={post.get_absolute_url(base_url=settings.portal_url)}]{post.id}[/link]",
            post.title,
            post.description_plain_text,
        )
    return table


def user_login_info(user: ListSystemUsersElement) -> str:
    results = (
        [LoginProviderEnum.CUSTOM.value] if LoginProviderEnum.CUSTOM in user.login_providers else []
    )
    for provider in [lp for lp in LoginProviderEnum if lp != LoginProviderEnum.CUSTOM]:
        provider_account_id = getattr(user, f"{provider}_account_id")
        if not provider_account_id:
            continue
        color = "green" if provider_account_id == user.contact_email else "red"
        out_provider = f"[{color}]{provider.value}: {provider_account_id} [/{color}]"
        results.append(out_provider)
    return "\n".join(results)
