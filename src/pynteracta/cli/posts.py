# SPDX-License-Identifier: Apache-2.0
"""posts sub-commands: get, list, comments."""

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
) -> None:
    """Fetch a single post by ID."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            post = client.posts.get(post_id)
            web_url = client.web_urls.post(post_id) if show_web_url else None
        fmt = resolve_output(state, output)
        if full or fields is not None:
            full_data = dump_full(post, exclude_none=fields is None)
            if web_url is not None:
                full_data["web_url"] = web_url
            if fields is not None:
                field_list = [f.strip() for f in fields.split(",") if f.strip()]
                rendered: dict[str, object] = select_fields(full_data, field_list)
            else:
                rendered = full_data
            print_output(rendered, fmt, console=console, title=f"Post {post_id}")
        else:
            data: dict[str, object] = {
                "id": post.id,
                "title": post.title,
                "community_id": post.community_id,
                "description": post.description_plain_text,
                "creation_ts": post.creation_timestamp,
                "last_modify_ts": post.last_modify_timestamp,
                "comments_count": post.comments_count,
                "likes_count": post.likes_count,
            }
            if web_url is not None:
                data["web_url"] = web_url
            print_output(data, fmt, console=console, title=f"Post {post_id}")
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
) -> None:
    """List posts in a community."""
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

            if full or fields is not None:
                render_output(
                    fmt,
                    items,
                    _curated,
                    full=full,
                    fields=fields,
                    extra_fn=_extra if show_web_url else None,
                    console=console,
                    title=title,
                )
            else:
                rows: list[dict[str, object]] = [_curated(item) for item in items]
                print_output(rows, fmt, console=console, title=title)
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
) -> None:
    """List comments on a post."""
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    try:
        with build_client(state) as client:
            items = []
            if all_pages:
                for item in client.posts.iterate_comments(post_id, page_size=page_size):
                    items.append(item)
            else:
                result = client.posts.comments(post_id, page_size=page_size)
                items = list(result.items_typed)

        fmt = resolve_output(state, output)
        title = f"Comments (post {post_id})"
        if full or fields is not None:

            def _curated_comment(obj: object) -> dict[str, object]:
                return {
                    "id": getattr(obj, "id", None),
                    "text": getattr(obj, "commentPlainText", None),
                    "creation_ts": getattr(obj, "creationTimestamp", None),
                }

            render_output(
                fmt,
                items,
                _curated_comment,
                full=full,
                fields=fields,
                console=console,
                title=title,
            )
        else:
            rows: list[dict[str, object]] = [
                {
                    "id": getattr(item, "id", None),
                    "text": getattr(item, "commentPlainText", None),
                    "creation_ts": getattr(item, "creationTimestamp", None),
                }
                for item in items
            ]
            print_output(rows, fmt, console=console, title=title)
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
