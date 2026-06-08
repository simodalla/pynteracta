# SPDX-License-Identifier: Apache-2.0
"""posts sub-commands: get, list, comments."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.api._utils import snake_to_camel
from pynteracta.api.posts import POST_ORDER_FIELDS
from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    EpochMs,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    handle_error,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.post_filters import PostFieldFilter

app = typer.Typer(help="Post commands.", no_args_is_help=True)


def _post_element_to_row(item: object, *, web_url: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {}
    if hasattr(item, "id"):
        row["id"] = getattr(item, "id", None)
    if hasattr(item, "title"):
        row["title"] = getattr(item, "title", None)
    if hasattr(item, "communityId"):
        row["community_id"] = getattr(item, "communityId", None)
    if hasattr(item, "creationTimestamp"):
        v = getattr(item, "creationTimestamp", None)
        row["creation_ts"] = EpochMs(v) if v is not None else None
    if web_url is not None:
        row["web_url"] = web_url
    return row


@app.command("get")
def posts_get(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
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
    """Fetch a single post by ID."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            post = client.posts.get(post_id)
            web_url = client.web_urls.post(post_id) if show_web_url else None

        def _curated(obj: object) -> dict[str, object]:
            cts = getattr(obj, "creation_timestamp", None)
            lmts = getattr(obj, "last_modify_timestamp", None)
            return {
                "id": getattr(obj, "id", None),
                "title": getattr(obj, "title", None),
                "community_id": getattr(obj, "community_id", None),
                "description": getattr(obj, "description_plain_text", None),
                "creation_ts": EpochMs(cts) if cts is not None else None,
                "last_modify_ts": EpochMs(lmts) if lmts is not None else None,
                "comments_count": getattr(obj, "comments_count", None),
                "likes_count": getattr(obj, "likes_count", None),
                **({"web_url": web_url} if web_url is not None else {}),
            }

        def _extra(obj: object) -> dict[str, Any]:
            return {"web_url": web_url} if web_url is not None else {}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [post],
            _curated,
            full=full,
            fields=fields,
            extra_fn=_extra if show_web_url else None,
            console=console,
            title=f"Post {post_id}",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


def _parse_field_filter(value: str) -> PostFieldFilter:
    """Parse ``COLUMN:TYPE:VAL[,VAL...]`` into a :class:`PostFieldFilter`.

    Token coercion: integer literal (``^-?\\d+$``) → int, otherwise str.
    COLUMN and TYPE are always int.
    """
    parts = value.split(":", 2)
    if len(parts) != 3:  # noqa: PLR2004
        raise typer.BadParameter(f"--field-filter must be COLUMN:TYPE:VAL[,VAL...], got: {value!r}")
    try:
        col = int(parts[0])
        tid = int(parts[1])
    except ValueError as err:
        raise typer.BadParameter(
            f"--field-filter COLUMN and TYPE must be integers, got: {value!r}"
        ) from err
    raw_params = parts[2].split(",") if parts[2] else []
    params: list[int | str | float] = []
    for tok in raw_params:
        try:
            params.append(int(tok))
        except ValueError:
            params.append(tok)
    return PostFieldFilter(column_id=col, type_id=tid, parameters=params)


@app.command("list")
def posts_list(  # noqa: PLR0913
    ctx: typer.Context,
    community: Annotated[int, typer.Option("--community", help="Community ID (required).")],
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
    # --- ordering ---
    order_by: Annotated[
        str | None,
        typer.Option(
            "--order-by",
            help=(
                "Sort field. Allowed values: "
                + ", ".join(POST_ORDER_FIELDS)
                + ". Dynamic form: postCustomField-<id>."
            ),
        ),
    ] = None,
    order_desc: Annotated[
        bool,
        typer.Option("--desc/--asc", help="Descending (default) or ascending sort."),
    ] = True,
    pinned_first: Annotated[
        bool | None,
        typer.Option("--pinned-first/--no-pinned-first", help="Pinned posts first."),
    ] = None,
    # --- common filters ---
    title: Annotated[
        str | None,
        typer.Option("--title", help="Filter on post title."),
    ] = None,
    contains_text: Annotated[
        str | None,
        typer.Option("--contains-text", help="Full-text filter on post content."),
    ] = None,
    created_by: Annotated[
        list[int] | None,
        typer.Option("--created-by", help="Filter by creator user id (repeatable)."),
    ] = None,
    hashtag: Annotated[
        list[int] | None,
        typer.Option("--hashtag", help="Filter by hashtag id (repeatable)."),
    ] = None,
    post_type: Annotated[
        list[int] | None,
        typer.Option("--post-type", help="Post type id (repeatable)."),
    ] = None,
    workflow_status: Annotated[
        list[int] | None,
        typer.Option("--workflow-status", help="Filter by workflow status id (repeatable)."),
    ] = None,
    created_from: Annotated[
        str | None,
        typer.Option("--created-from", help="Creation date lower bound (ISO-8601 or epoch-ms)."),
    ] = None,
    created_to: Annotated[
        str | None,
        typer.Option("--created-to", help="Creation date upper bound (ISO-8601 or epoch-ms)."),
    ] = None,
    followed_by_me: Annotated[
        bool | None,
        typer.Option("--followed-by-me/--no-followed-by-me", help="Only posts followed by me."),
    ] = None,
    to_manage: Annotated[
        bool | None,
        typer.Option("--to-manage/--no-to-manage", help="Only posts with pending actions."),
    ] = None,
    only_pinned: Annotated[
        bool | None,
        typer.Option("--only-pinned/--no-only-pinned", help="Only pinned posts."),
    ] = None,
    # --- custom-field filters ---
    field_filter: Annotated[
        list[str] | None,
        typer.Option(
            "--field-filter",
            help=(
                "Custom-field filter: COLUMN_ID:TYPE_ID:VAL[,VAL...]. "
                "TYPE_ID: 1=EQUAL 2=INTERVAL 3=LIKE 4=IN 5=CONTAINS 6=IS_NULL_OR_IN 7=IS_EMPTY. "
                "Numeric tokens are coerced to int. Repeatable."
            ),
        ),
    ] = None,
    # --- generic escape hatch ---
    filter_kv: Annotated[
        list[str] | None,
        typer.Option(
            "--filter",
            help=(
                "Generic filter key=value (string-only passthrough, snake_case keys). "
                "For typed filters use the dedicated flags. Repeatable."
            ),
        ),
    ] = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List posts in a community with filtering and ordering.

    Examples::

        # Order by last modification, most recent first
        pynteracta posts list --community 56 --order-by postLastModifyTimestamp --desc

        # Filter by title and post type
        pynteracta posts list --community 56 --title "Report" --post-type 1

        # Custom-field filter: column 1411 IN [226, 512]
        pynteracta posts list --community 56 --field-filter 1411:4:226,512

        # Date range on custom datetime field (epoch-ms)
        pynteracta posts list --community 56 --field-filter 1954:2:1780264800000,1780955999999

        # Generic passthrough for long-tail filters
        pynteracta posts list --community 56 --filter mentioned=true
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)

    # Parse --field-filter
    parsed_field_filters: list[PostFieldFilter] | None = None
    if field_filter:
        try:
            parsed_field_filters = [_parse_field_filter(v) for v in field_filter]
        except typer.BadParameter as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1) from exc

    # Parse --filter key=value (string-only)
    extra_filters: dict[str, Any] = {}
    for kv in filter_kv or []:
        if "=" not in kv:
            console.print(f"[red]Error:[/red] --filter must be key=value, got: {kv!r}")
            raise typer.Exit(1)
        k, v = kv.split("=", 1)
        extra_filters[snake_to_camel(k.strip())] = v.strip()

    # order_desc is only meaningful when order_by is set; avoid sending it otherwise
    effective_order_desc = order_desc if order_by is not None else None

    try:
        with build_client(state) as client:
            items = []
            call_kwargs: dict[str, Any] = dict(
                page_size=page_size,
                order_by=order_by,
                order_desc=effective_order_desc,
                pinned_first=pinned_first,
                title=title,
                contains_text=contains_text,
                created_by_user_ids=created_by or None,
                hashtag_ids=hashtag or None,
                post_types=post_type or None,
                current_workflow_status_ids=workflow_status or None,
                creation_timestamp_from=created_from,
                creation_timestamp_to=created_to,
                followed_by_me=followed_by_me,
                to_manage=to_manage,
                only_pinned=only_pinned,
                post_field_filters=parsed_field_filters,
                community_post_filters=extra_filters or None,
            )
            if all_pages:
                for item in client.posts.iterate_in_community(community, **call_kwargs):
                    items.append(item)
            else:
                result = client.posts.list_in_community(community, **call_kwargs)
                items = list(result.items_typed)

            fmt = resolve_output(state, output)
            title_str = f"Posts (community {community})"

            def _curated(obj: object) -> dict[str, object]:
                pid = getattr(obj, "id", None)
                wu = client.web_urls.post(int(pid)) if show_web_url and pid else None
                return _post_element_to_row(obj, web_url=wu)

            def _extra(obj: object) -> dict[str, Any]:
                pid = getattr(obj, "id", None)
                return {"web_url": client.web_urls.post(int(pid))} if show_web_url and pid else {}

            render_output(
                fmt,
                items,
                _curated,
                full=full,
                fields=fields,
                extra_fn=_extra if show_web_url else None,
                console=console,
                title=title_str,
                export_path=export,
                export_format=export_format,
                quiet=state.quiet,
            )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("get-by-client-uid")
def posts_get_by_client_uid(  # noqa: PLR0913
    ctx: typer.Context,
    client_uid: Annotated[str, typer.Argument(help="Post client UID.")],
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
    """Fetch a single post by client UID."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            post = client.posts.get_by_client_uid(client_uid)
            web_url = client.web_urls.post(post.id) if show_web_url and post.id else None

        def _curated(obj: object) -> dict[str, object]:
            cts = getattr(obj, "creation_timestamp", None)
            lmts = getattr(obj, "last_modify_timestamp", None)
            return {
                "id": getattr(obj, "id", None),
                "title": getattr(obj, "title", None),
                "community_id": getattr(obj, "community_id", None),
                "description": getattr(obj, "description_plain_text", None),
                "creation_ts": EpochMs(cts) if cts is not None else None,
                "last_modify_ts": EpochMs(lmts) if lmts is not None else None,
                "comments_count": getattr(obj, "comments_count", None),
                "likes_count": getattr(obj, "likes_count", None),
                **({"web_url": web_url} if web_url is not None else {}),
            }

        def _extra(obj: object) -> dict[str, Any]:
            return {"web_url": web_url} if web_url is not None else {}

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [post],
            _curated,
            full=full,
            fields=fields,
            extra_fn=_extra if show_web_url else None,
            console=console,
            title=f"Post (clientUid={client_uid})",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("capabilities")
def posts_capabilities(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Fetch capability flags for a post."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            caps = client.posts.capabilities(post_id)

        def _curated(obj: object) -> dict[str, object]:
            return {
                "can_view_detail": getattr(obj, "can_view_detail", None),
                "can_modify": getattr(obj, "can_modify", None),
                "can_delete": getattr(obj, "can_delete", None),
                "can_view_comment": getattr(obj, "can_view_comment", None),
                "can_add_comment": getattr(obj, "can_add_comment", None),
                "can_edit_like": getattr(obj, "can_edit_like", None),
                "can_edit_follow": getattr(obj, "can_edit_follow", None),
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            [caps],
            _curated,
            full=full,
            fields=fields,
            console=console,
            title=f"Capabilities (post {post_id})",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
            single_command=True,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("history")
def posts_history(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List history events for a post."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.posts.iterate_history(post_id, page_size=page_size):
                    items.append(item)
            else:
                result = client.posts.history(post_id, page_size=page_size)
                items = list(result.items_typed)

        def _curated(obj: object) -> dict[str, object]:
            ts = getattr(obj, "timestamp", None)
            return {
                "id": getattr(obj, "id", None),
                "type_id": getattr(obj, "typeId", None),
                "type_description": getattr(obj, "typeDescription", None),
                "timestamp": EpochMs(ts) if ts is not None else None,
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            _curated,
            full=full,
            fields=fields,
            console=console,
            title=f"History (post {post_id})",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("global-stream")
def posts_global_stream(  # noqa: PLR0913
    ctx: typer.Context,
    sync_token: Annotated[
        str | None,
        typer.Option("--sync-token", help="Sync token for incremental polling."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Stream posts created/modified/deleted across all communities."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.posts.iterate_global_stream(sync_token=sync_token):
                    items.append(item)
            else:
                result = client.posts.global_stream(sync_token=sync_token)
                items = list(result.items_typed)

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            _post_element_to_row,
            full=full,
            fields=fields,
            console=console,
            title="Global stream",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("community-list")
def posts_community_list(  # noqa: PLR0913
    ctx: typer.Context,
    community: Annotated[int, typer.Option("--community", help="Community ID (required).")],
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
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List posts in a community (data/community-list endpoint, basic filters).

    Distinct from ``posts list`` which uses the more fully-featured
    ``data/list/community`` endpoint with extended filter support.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.posts.iterate_community_list(community, page_size=page_size):
                    items.append(item)
            else:
                result = client.posts.community_list(community, page_size=page_size)
                items = list(result.items_typed)

            fmt = resolve_output(state, output)

            def _curated(obj: object) -> dict[str, object]:
                pid = getattr(obj, "id", None)
                wu = client.web_urls.post(int(pid)) if show_web_url and pid else None
                return _post_element_to_row(obj, web_url=wu)

            def _extra(obj: object) -> dict[str, Any]:
                pid = getattr(obj, "id", None)
                return {"web_url": client.web_urls.post(int(pid))} if show_web_url and pid else {}

            render_output(
                fmt,
                items,
                _curated,
                full=full,
                fields=fields,
                extra_fn=_extra if show_web_url else None,
                console=console,
                title=f"Posts community-list (community {community})",
                export_path=export,
                export_format=export_format,
                quiet=state.quiet,
            )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("check-visibility")
def posts_check_visibility(  # noqa: PLR0913
    ctx: typer.Context,
    post_ids: Annotated[list[int], typer.Argument(help="Post IDs to check.")],
    with_comments: Annotated[
        bool,
        typer.Option("--with-comments", help="Also resolve comment visibility."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Check which posts are visible to the current user."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            if with_comments:
                result = client.posts.check_visibility_with_comments(post_ids)
            else:
                result = client.posts.check_visibility(post_ids)
            items = result.posts_typed

        def _curated(obj: object) -> dict[str, object]:
            row: dict[str, object] = {"id": getattr(obj, "id", None)}
            can_view = getattr(obj, "canViewComments", None)
            if can_view is not None:
                row["can_view_comments"] = can_view
            return row

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            _curated,
            full=full,
            fields=fields,
            console=console,
            title="Visibility check",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("comments")
def posts_comments(  # noqa: PLR0913
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    page_size: Annotated[
        int | None,
        typer.Option("--page-size", help="Items per page."),
    ] = None,
    all_pages: Annotated[
        bool,
        typer.Option("--all", help="Iterate through all pages."),
    ] = False,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List comments on a post."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.posts.iterate_comments(post_id, page_size=page_size):
                    items.append(item)
            else:
                result = client.posts.comments(post_id, page_size=page_size)
                items = list(result.items_typed)

        def _curated_comment(obj: object) -> dict[str, object]:
            cts = getattr(obj, "creationTimestamp", None)
            return {
                "id": getattr(obj, "id", None),
                "text": getattr(obj, "commentPlainText", None),
                "creation_ts": EpochMs(cts) if cts is not None else None,
            }

        fmt = resolve_output(state, output)
        render_output(
            fmt,
            items,
            _curated_comment,
            full=full,
            fields=fields,
            console=console,
            title=f"Comments (post {post_id})",
            export_path=export,
            export_format=export_format,
            quiet=state.quiet,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
