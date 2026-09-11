# SPDX-License-Identifier: Apache-2.0
"""users sub-commands: list, get-for-edit, me, profile."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    _check_paging_flags,
    _echo_next_page_token,
    _print_count,
    build_client,
    handle_error,
    make_console,
    parse_kv_filters,
    render_output,
    resolve_output,
    validate_export_options,
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
        typer.Option("--full-text", help="Full-text filter on name, surname, and email."),
    ] = None,
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    page_token: Annotated[
        str | None,
        typer.Option(
            "--page-token",
            help="Fetch the page identified by this token (see 'Next page token' on stderr).",
        ),
    ] = None,
    count: Annotated[
        bool,
        typer.Option("--count", help="Print only the total number of matching users and exit."),
    ] = False,
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include Web URL in output."),
    ] = False,
    # --- filters ---
    status: Annotated[
        list[int] | None,
        typer.Option("--status", help="Filter by user status id (repeatable)."),
    ] = None,
    workspace: Annotated[
        list[int] | None,
        typer.Option("--workspace", help="Filter by workspace id (repeatable)."),
    ] = None,
    community: Annotated[
        list[int] | None,
        typer.Option("--community", help="Filter by community id (repeatable)."),
    ] = None,
    role: Annotated[
        str | None,
        typer.Option("--role", help="Filter by role."),
    ] = None,
    created_from: Annotated[
        str | None,
        typer.Option("--created-from", help="Creation date lower bound (ISO-8601 or epoch-ms)."),
    ] = None,
    created_to: Annotated[
        str | None,
        typer.Option("--created-to", help="Creation date upper bound (ISO-8601 or epoch-ms)."),
    ] = None,
    last_access_from: Annotated[
        str | None,
        typer.Option(
            "--last-access-from", help="Last-access date lower bound (ISO-8601 or epoch-ms)."
        ),
    ] = None,
    last_access_to: Annotated[
        str | None,
        typer.Option(
            "--last-access-to", help="Last-access date upper bound (ISO-8601 or epoch-ms)."
        ),
    ] = None,
    # --- ordering ---
    order_by: Annotated[
        str | None,
        typer.Option("--order-by", help="Sort field id (mapped to orderTypeId)."),
    ] = None,
    order_desc: Annotated[
        bool | None,
        typer.Option("--desc/--asc", help="Descending or ascending sort."),
    ] = None,
    # --- generic escape hatch ---
    filter_kv: Annotated[
        list[str] | None,
        typer.Option(
            "--filter",
            help=(
                "Generic filter key=value (snake_case keys; true/false and integers are typed, "
                "everything else is a string). Repeatable."
            ),
        ),
    ] = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List system users with filtering and ordering.

    Examples::

        # Full-text filter
        pynteracta users list --full-text rossi

        # Filter by status and workspace (repeatable)
        pynteracta users list --status 1 --status 2 --workspace 10

        # Users who have not logged in since 2026-01-01
        pynteracta users list --last-access-to 2026-01-01

        # How many blocked-profile users match / resume from a page token
        pynteracta users list --status 2 --count
        pynteracta users list --page-token eyJwYWdlIjoyfQ

        # Order by a sort field id, ascending
        pynteracta users list --order-by lastName --asc

        # Generic passthrough for long-tail string filters
        pynteracta users list --filter external_id_full_text_filter=EXT-1
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    _check_paging_flags(console, all_pages=all_pages, page_token=page_token, count=count)

    # Parse --filter key=value (typed tokens)
    try:
        extra_filters = parse_kv_filters(filter_kv)
    except typer.BadParameter as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    try:
        with build_client(state) as client:
            items = []
            call_kwargs: dict[str, Any] = dict(
                full_text_filter=full_text,
                status_filter=status or None,
                workspace_ids=workspace or None,
                community_ids=community or None,
                role=role,
                creation_timestamp_from=created_from,
                creation_timestamp_to=created_to,
                last_access_timestamp_from=last_access_from,
                last_access_timestamp_to=last_access_to,
                order_by=order_by,
                order_desc=order_desc,
                **extra_filters,
            )
            if count:
                total = client.users.list(
                    page_size=1, calculate_total_items_count=True, **call_kwargs
                ).total_items_count
                raise typer.Exit(_print_count(console, total))
            if all_pages:
                for item in client.users.iterate(page_size=page_size, **call_kwargs):
                    items.append(item)
            else:
                result = client.users.list(
                    page_size=page_size, page_token=page_token, **call_kwargs
                )
                items = list(result.items_typed)
                _echo_next_page_token(result.next_page_token, quiet=state.quiet)

            fmt = resolve_output(state, output)

            def _curated(obj: object) -> dict[str, object]:
                uid = getattr(obj, "id", None)
                wu = client.web_urls.user(int(uid)) if show_web_url and uid else None
                return _user_element_to_row(obj, web_url=wu)

            def _extra(obj: object) -> dict[str, Any]:
                uid = getattr(obj, "id", None)
                return {"web_url": client.web_urls.user(int(uid))} if show_web_url and uid else {}

            render_output(
                fmt,
                items,
                _curated,
                full=full,
                fields=fields,
                extra_fn=_extra if show_web_url else None,
                console=console,
                title="Users",
                export_path=export,
                export_format=export_format,
                quiet=state.quiet,
            )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("me")
def users_me(  # noqa: PLR0913
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show identity of the authenticated principal (GET /core/auth/current-user-data)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            me = client.users.me()

        def _curated_me(obj: object) -> dict[str, object]:
            ud = getattr(obj, "user_data_typed", None)
            if ud is not None:
                return ud.model_dump(mode="json", exclude_none=True)  # type: ignore[no-any-return]
            return {
                "has_google_credentials": getattr(obj, "has_google_credentials", None),
                "has_microsoft_credentials": getattr(obj, "has_microsoft_credentials", None),
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [me],
            _curated_me,
            full=full,
            fields=fields,
            console=console,
            title="Current User",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("profile")
def users_profile(  # noqa: PLR0913
    ctx: typer.Context,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Show people-directory profile (GET /core/user-profile/info)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            prof = client.users.profile()

        def _curated_profile(obj: object) -> dict[str, object]:
            return {
                "id": getattr(obj, "id", None),
                "first_name": getattr(obj, "first_name", None),
                "last_name": getattr(obj, "last_name", None),
                "caption": getattr(obj, "caption", None),
                "contact_email": getattr(obj, "contact_email", None),
                "account_photo_url": getattr(obj, "account_photo_url", None),
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [prof],
            _curated_profile,
            full=full,
            fields=fields,
            console=console,
            title="User Profile",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
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
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch a user record for editing (requires admin permissions)."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            user = client.users.get_for_edit(user_id)
            web_url = client.web_urls.user(user_id) if show_web_url else None

        def _curated(obj: object) -> dict[str, object]:
            return {
                "first_name": getattr(obj, "first_name", None),
                "last_name": getattr(obj, "last_name", None),
                "contact_email": getattr(obj, "contact_email", None),
                "external_id": getattr(obj, "external_id", None),
                "blocked": getattr(obj, "blocked", None),
                "account_photo_url": getattr(obj, "account_photo_url", None),
                **({"web_url": web_url} if web_url is not None else {}),
            }

        def _extra(obj: object) -> dict[str, Any]:
            return {"web_url": web_url} if web_url is not None else {}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [user],
            _curated,
            full=full,
            fields=fields,
            extra_fn=_extra if show_web_url else None,
            console=console,
            title=f"User {user_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
