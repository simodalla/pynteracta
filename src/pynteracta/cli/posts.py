# SPDX-License-Identifier: Apache-2.0
"""posts sub-commands: get, list, comments."""

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
    build_client,
    handle_error,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.exceptions import InteractaError

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
        row["creation_ts"] = getattr(item, "creationTimestamp", None)
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
            return {
                "id": getattr(obj, "id", None),
                "title": getattr(obj, "title", None),
                "community_id": getattr(obj, "community_id", None),
                "description": getattr(obj, "description_plain_text", None),
                "creation_ts": getattr(obj, "creation_timestamp", None),
                "last_modify_ts": getattr(obj, "last_modify_timestamp", None),
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


@app.command("list")
def posts_list(  # noqa: PLR0913
    ctx: typer.Context,
    community: Annotated[int, typer.Option("--community", help="Community ID (required).")],
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
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """List posts in a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)

    filters: dict[str, Any] = {}
    if full_text is not None:
        filters["full_text_filter"] = full_text

    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.posts.iterate_in_community(
                    community, page_size=page_size, **filters
                ):
                    items.append(item)
            else:
                result = client.posts.list_in_community(community, page_size=page_size, **filters)
                items = list(result.items_typed)

            fmt = resolve_output(state, output)
            title = f"Posts (community {community})"

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
                title=title,
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
            return {
                "id": getattr(obj, "id", None),
                "title": getattr(obj, "title", None),
                "community_id": getattr(obj, "community_id", None),
                "description": getattr(obj, "description_plain_text", None),
                "creation_ts": getattr(obj, "creation_timestamp", None),
                "last_modify_ts": getattr(obj, "last_modify_timestamp", None),
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
            return {
                "id": getattr(obj, "id", None),
                "type_id": getattr(obj, "typeId", None),
                "type_description": getattr(obj, "typeDescription", None),
                "timestamp": getattr(obj, "timestamp", None),
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
            return {
                "id": getattr(obj, "id", None),
                "text": getattr(obj, "commentPlainText", None),
                "creation_ts": getattr(obj, "creationTimestamp", None),
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
