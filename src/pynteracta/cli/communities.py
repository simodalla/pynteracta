# SPDX-License-Identifier: Apache-2.0
"""communities sub-commands: list, details, post-definition, post-definitions."""

from __future__ import annotations

from typing import Annotated

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
from pynteracta.models.facade.communities import FieldType

app = typer.Typer(help="Community settings commands.", no_args_is_help=True)


@app.command("list")
def communities_list(ctx: typer.Context) -> None:
    """List communities the caller can post in (GET /communication/settings/communities)."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            result = client.communities.list()
            rows: list[dict[str, object]] = [
                {"id": c.id, "name": c.name} for c in result.items_typed
            ]
        print_output(rows, state.output, console=console, title="Communities")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("details")
def communities_details(
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
    show_web_url: Annotated[
        bool,
        typer.Option("--web-url", help="Include Web URL in output."),
    ] = False,
) -> None:
    """Show details for a single community."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            result = client.communities.details(community_id)
            community = result.community
            data: dict[str, object] = {
                "id": community.id if community else None,
                "name": community.name if community else None,
                "description": community.description if community else None,
            }
            if show_web_url:
                data["web_url"] = client.web_urls.community(community_id)
        print_output(data, state.output, console=console, title=f"Community {community_id}")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("details-bulk")
def communities_details_bulk(
    ctx: typer.Context,
    ids: Annotated[
        list[int],
        typer.Option("--id", help="Community ID (repeat for multiple)."),
    ],
) -> None:
    """Show details for multiple communities (POST /communication/settings/communities/details)."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            result = client.communities.details_bulk(ids)
            rows: list[dict[str, object]] = [
                {"id": c.id, "name": c.name} for c in result.items_typed
            ]
        print_output(rows, state.output, console=console, title="Communities")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("post-definition")
def communities_post_definition(
    ctx: typer.Context,
    community_id: Annotated[int, typer.Argument(help="Community ID.")],
) -> None:
    """Show the post structure (field definitions) for a community."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            defn = client.communities.post_definition(community_id)
            rows: list[dict[str, object]] = []
            for f in defn.field_definitions:
                ft = f.type
                rows.append(
                    {
                        "id": f.id,
                        "name": f.name,
                        "label": f.label,
                        "type": ft.name if ft is not None else f.type_raw,
                        "required": f.required,
                    }
                )
        print_output(
            rows,
            state.output,
            console=console,
            title=f"Post Definition — Community {community_id}",
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("post-definitions")
def communities_post_definitions(
    ctx: typer.Context,
    ids: Annotated[
        list[int],
        typer.Option("--id", help="Community ID (repeat for multiple)."),
    ],
) -> None:
    """Show post definitions for multiple communities."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            defn_map = client.communities.post_definitions(ids)
            rows: list[dict[str, object]] = []
            for community_id, defn in sorted(defn_map.definitions.items()):
                for f in defn.field_definitions:
                    ft = f.type
                    rows.append(
                        {
                            "community_id": community_id,
                            "field_id": f.id,
                            "label": f.label,
                            "type": ft.name if ft is not None else f.type_raw,
                            "required": f.required,
                        }
                    )
        print_output(rows, state.output, console=console, title="Post Definitions")
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


# Keep FieldType in scope so it's importable from this module for tests.
__all__ = ["FieldType", "app"]
