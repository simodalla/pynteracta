# SPDX-License-Identifier: Apache-2.0
"""config sub-commands: set, get, list, use-profile."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Annotated, Any

import tomlkit
import typer

from pynteracta.cli._common import (
    EXIT_SUCCESS,
    CliState,
    config_path_from_state,
    make_console,
    print_output,
)

app = typer.Typer(help="Configuration commands.", no_args_is_help=True)


def _load_doc(config_path: Path) -> tuple[Any, bool]:
    if config_path.exists():
        return tomlkit.loads(config_path.read_text(encoding="utf-8")), True
    return tomlkit.document(), False


def _ensure_profile_table(doc: Any, profile_name: str) -> Any:
    profiles_table = doc.get("profiles")
    if profiles_table is None:
        profiles_table = tomlkit.table()
        doc.add("profiles", profiles_table)
    if profile_name not in profiles_table:
        profiles_table.add(profile_name, tomlkit.table())
    return profiles_table


@app.command("set")
def config_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Config key (e.g. base_url).")],
    value: Annotated[str, typer.Argument(help="Value to set.")],
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile to update."),
    ] = None,
) -> None:
    """Set a config value in the active (or named) profile."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)
    doc, existed = _load_doc(config_path)
    if not existed:
        config_path.parent.mkdir(parents=True, exist_ok=True)

    effective_profile = profile or state.profile or "default"
    profiles_table = _ensure_profile_table(doc, effective_profile)
    profiles_table[effective_profile][key] = value
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(
        f"[green]✓[/green] Set [bold]{key}[/bold] = {value!r} in profile '{effective_profile}'"
    )
    raise typer.Exit(EXIT_SUCCESS)


@app.command("get")
def config_get(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Config key to retrieve.")],
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile to read from."),
    ] = None,
) -> None:
    """Get a config value from the active (or named) profile."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)

    if not config_path.exists():
        typer.echo("No config file found.", err=True)
        raise typer.Exit(1)

    raw: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8"))
    current_profile: str = str(raw.get("current_profile", "default"))
    effective_profile = profile or state.profile or current_profile
    profiles: dict[str, Any] = raw.get("profiles", {})
    prof_data: dict[str, Any] = profiles.get(effective_profile, {})

    if key not in prof_data:
        typer.echo(f"Key '{key}' not found in profile '{effective_profile}'.", err=True)
        raise typer.Exit(1)

    console.print(str(prof_data[key]))
    raise typer.Exit(EXIT_SUCCESS)


@app.command("list")
def config_list(
    ctx: typer.Context,
    profile: Annotated[
        str | None,
        typer.Option("--profile", help="Profile to list (all if omitted)."),
    ] = None,
) -> None:
    """List all configuration profiles (or a specific one)."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)

    if not config_path.exists():
        typer.echo("No config file found.", err=True)
        raise typer.Exit(0)

    raw: dict[str, Any] = tomllib.loads(config_path.read_text(encoding="utf-8"))
    profiles: dict[str, Any] = raw.get("profiles", {})
    current: str = str(raw.get("current_profile", "default"))

    if profile is not None:
        profiles = {k: v for k, v in profiles.items() if k == profile}

    rows: list[dict[str, Any]] = []
    for prof_name, prof_data in profiles.items():
        if isinstance(prof_data, dict):
            for k, v in prof_data.items():
                active = " *" if prof_name == current else ""
                rows.append({"profile": prof_name + active, "key": k, "value": str(v)})

    print_output(rows, state.output, console=console, title="Configuration")
    raise typer.Exit(EXIT_SUCCESS)


@app.command("add-profile")
def add_profile(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="New profile name.")],
    base_url: Annotated[
        str | None,
        typer.Option("--base-url", help="Tenant URL for the new profile."),
    ] = None,
) -> None:
    """Add a new profile to config.toml."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)
    doc, existed = _load_doc(config_path)
    if not existed:
        config_path.parent.mkdir(parents=True, exist_ok=True)

    profiles_table = _ensure_profile_table(doc, name)
    if base_url is not None:
        profiles_table[name]["base_url"] = base_url
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(f"[green]✓[/green] Profile '{name}' added.")
    raise typer.Exit(EXIT_SUCCESS)


@app.command("remove-profile")
def remove_profile(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name to remove.")],
) -> None:
    """Remove a profile from config.toml."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)

    if not config_path.exists():
        typer.echo("No config file found.", err=True)
        raise typer.Exit(1)

    doc, _ = _load_doc(config_path)
    profiles_table = doc.get("profiles")
    if profiles_table is None or name not in profiles_table:
        typer.echo(f"Profile '{name}' not found.", err=True)
        raise typer.Exit(1)

    del profiles_table[name]
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(f"[green]✓[/green] Profile '{name}' removed.")
    raise typer.Exit(EXIT_SUCCESS)


@app.command("use-profile")
def use_profile(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name to activate.")],
) -> None:
    """Set the active profile in config.toml."""
    state: CliState = ctx.obj
    console = make_console(state)
    config_path = config_path_from_state(state)
    doc, existed = _load_doc(config_path)
    if not existed:
        config_path.parent.mkdir(parents=True, exist_ok=True)

    doc["current_profile"] = name
    config_path.write_text(tomlkit.dumps(doc), encoding="utf-8")
    console.print(f"[green]✓[/green] Active profile set to '{name}'.")
    raise typer.Exit(EXIT_SUCCESS)
