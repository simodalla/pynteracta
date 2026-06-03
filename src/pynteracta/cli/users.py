# SPDX-License-Identifier: Apache-2.0
"""users sub-commands: list, get-for-edit, me, profile."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    dump_full,
    handle_error,
    make_console,
    print_output,
    render_output,
    resolve_output,
    select_fields,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError

app = typer.Typer(help="User commands.", no_args_is_help=True)


def _user_element_to_row(item: object, *, web_url: str | None = None) -> dict[str, object]:
    """Convert a ListSystemUsersElementDTOModel to a display dict."""
    row: dict[str, object] = {}
    if hasattr(item, "id"):
        row["id"] = getattr(item, "id", None)
    if hasattr(item, "firstName"):
        row["first_name"] = getattr(item, "firstName", None)
    if hasattr(item, "lastName"):
        row["last_name"] = getattr(item, "lastName", None)
    if hasattr(item, "contactEmail"):
        row["email"] = getattr(item, "contactEmail", None)
    if web_url is not None:
        row["web_url"] = web_url
    return row


@app.command("list")
def users_list(  # noqa: PLR0913
    ctx: typer.Context,
    full_text: Annotated[
        str | None,
        typer.Option("--full-text", help="Full-text filter."),
    ] = None,
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include Web URL in output."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """List system users."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)

    filters: dict[str, Any] = {}
    if full_text is not None:
        filters["full_text_filter"] = full_text

    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.users.iterate(page_size=page_size, **filters):
                    items.append(item)
            else:
                result = client.users.list(page_size=page_size, **filters)
                items = list(result.items_typed)

            if full or fields is not None:
                fmt = resolve_output(state, output)

                def curated(obj: object) -> dict[str, object]:
                    uid = getattr(obj, "id", None)
                    wu = client.web_urls.user(int(uid)) if show_web_url and uid else None
                    return _user_element_to_row(obj, web_url=wu)

                render_output(
                    fmt, items, curated, full=full, fields=fields, console=console, title="Users"
                )
            else:
                rows: list[dict[str, object]] = []
                for item in items:
                    uid = getattr(item, "id", None)
                    wu = client.web_urls.user(int(uid)) if show_web_url and uid else None
                    rows.append(_user_element_to_row(item, web_url=wu))
                print_output(rows, resolve_output(state, output), console=console, title="Users")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("me")
def users_me(
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show identity of the authenticated principal (GET /core/auth/current-user-data)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            me = client.users.me()
            ud = me.user_data_typed
            if ud is not None:
                curated: dict[str, object] = ud.model_dump(mode="json", exclude_none=True)
            else:
                curated = {
                    "has_google_credentials": me.has_google_credentials,
                    "has_microsoft_credentials": me.has_microsoft_credentials,
                }
        fmt = resolve_output(state, output)
        if full or fields is not None:
            full_data = dump_full(me)
            if fields is not None:
                field_list = [f.strip() for f in fields.split(",") if f.strip()]
                rendered: dict[str, object] = select_fields(full_data, field_list)
            else:
                rendered = full_data
            print_output(rendered, fmt, console=console, title="Current User")
        else:
            print_output(curated, fmt, console=console, title="Current User")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("profile")
def users_profile(
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Show people-directory profile (GET /core/user-profile/info)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            prof = client.users.profile()
        fmt = resolve_output(state, output)
        if full or fields is not None:
            full_data = dump_full(prof)
            if fields is not None:
                field_list = [f.strip() for f in fields.split(",") if f.strip()]
                rendered: dict[str, object] = select_fields(full_data, field_list)
            else:
                rendered = full_data
            print_output(rendered, fmt, console=console, title="User Profile")
        else:
            data: dict[str, object] = {
                "id": prof.id,
                "first_name": prof.first_name,
                "last_name": prof.last_name,
                "caption": prof.caption,
                "contact_email": prof.contact_email,
                "account_photo_url": prof.account_photo_url,
            }
            print_output(data, fmt, console=console, title="User Profile")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-for-edit")
def users_get_for_edit(  # noqa: PLR0913
    ctx: typer.Context,
    user_id: Annotated[int, typer.Argument(help="User ID (admin-only lookup).")],
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include Web URL in output."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
) -> None:
    """Fetch a user record for editing (requires admin permissions)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            user = client.users.get_for_edit(user_id)
            web_url = client.web_urls.user(user_id) if show_web_url else None
        fmt = resolve_output(state, output)
        if full or fields is not None:
            full_data = dump_full(user)
            if web_url is not None:
                full_data["web_url"] = web_url
            if fields is not None:
                field_list = [f.strip() for f in fields.split(",") if f.strip()]
                rendered: dict[str, object] = select_fields(full_data, field_list)
            else:
                rendered = full_data
            print_output(rendered, fmt, console=console, title=f"User {user_id}")
        else:
            data: dict[str, object] = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "contact_email": user.contact_email,
                "external_id": user.external_id,
                "blocked": user.blocked,
                "account_photo_url": user.account_photo_url,
            }
            if web_url is not None:
                data["web_url"] = web_url
            print_output(data, fmt, console=console, title=f"User {user_id}")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
