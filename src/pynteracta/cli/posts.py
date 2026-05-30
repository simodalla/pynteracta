# SPDX-License-Identifier: Apache-2.0
"""posts sub-commands: get, list, comments."""

from __future__ import annotations

from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    build_client,
    handle_error,
    make_console,
    print_output,
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
def posts_get(
    ctx: typer.Context,
    post_id: Annotated[int, typer.Argument(help="Post ID.")],
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include Web URL in output."),
    ] = False,
) -> None:
    """Fetch a single post by ID."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            post = client.posts.get(post_id)
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
            if show_web_url:
                data["web_url"] = client.web_urls.post(post_id)
        print_output(data, state.output, console=console, title=f"Post {post_id}")
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
) -> None:
    """List posts in a community."""
    state: CliState = ctx.obj
    console = make_console(state)

    filters: dict[str, Any] = {}
    if full_text is not None:
        filters["full_text_filter"] = full_text

    try:
        with build_client(state) as client:
            rows: list[dict[str, object]] = []
            if all_pages:
                for item in client.posts.iterate_in_community(
                    community, page_size=page_size, **filters
                ):
                    pid = getattr(item, "id", None)
                    wu = client.web_urls.post(int(pid)) if show_web_url and pid else None
                    rows.append(_post_element_to_row(item, web_url=wu))
            else:
                result = client.posts.list_in_community(community, page_size=page_size, **filters)
                for item in result.items_typed:
                    pid = getattr(item, "id", None)
                    wu = client.web_urls.post(int(pid)) if show_web_url and pid else None
                    rows.append(_post_element_to_row(item, web_url=wu))
        print_output(rows, state.output, console=console, title=f"Posts (community {community})")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("comments")
def posts_comments(
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
) -> None:
    """List comments on a post."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            rows: list[dict[str, object]] = []
            if all_pages:
                for item in client.posts.iterate_comments(post_id, page_size=page_size):
                    row: dict[str, object] = {
                        "id": getattr(item, "id", None),
                        "text": getattr(item, "commentPlainText", None),
                        "creation_ts": getattr(item, "creationTimestamp", None),
                    }
                    rows.append(row)
            else:
                result = client.posts.comments(post_id, page_size=page_size)
                for item in result.items_typed:
                    row = {
                        "id": getattr(item, "id", None),
                        "text": getattr(item, "commentPlainText", None),
                        "creation_ts": getattr(item, "creationTimestamp", None),
                    }
                    rows.append(row)
        print_output(rows, state.output, console=console, title=f"Comments (post {post_id})")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
