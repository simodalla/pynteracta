# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura di cataloghi e voci (spec 06), registrati sul gruppo ``catalogs``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``. Le
mappe per lingua (``--name``, ``--label``) si passano come ``LANG=TEXT`` ripetibili e si uniscono
chiave per chiave alla mappa di ``--json`` o del form letto.
"""

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
    load_json_body,
    make_console,
    render_output,
    resolve_output,
    validate_export_options,
    validate_full_fields,
)
from pynteracta.cli._write import (
    JsonBodyOption,
    merge_body,
    merge_lang_map,
    parse_lang_map,
    validate_body,
)
from pynteracta.cli.catalogs import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.catalogs import CatalogEntryWriteResult, CatalogWriteResult
from pynteracta.models.generated.external_v2 import (
    CreateEditCatalogEntryRequestDTO,
    CreateEditCatalogRequestDTO,
)

NameOption = Annotated[
    list[str] | None,
    typer.Option("--name", help="Catalog name as LANG=TEXT (repeatable; e.g. it=Sedi)."),
]
ParentOption = Annotated[int | None, typer.Option("--parent", help="Parent catalog ID.")]
LabelOption = Annotated[
    list[str] | None,
    typer.Option("--label", help="Entry label as LANG=TEXT (repeatable; e.g. it=Bologna)."),
]
ParentEntryOption = Annotated[
    list[int] | None,
    typer.Option("--parent-entry", help="Parent entry ID (repeatable)."),
]
ExternalIdOption = Annotated[
    str | None, typer.Option("--external-id", help="Unique external identifier of the entry.")
]


def _catalog_row(obj: object) -> dict[str, object]:
    """Tabella curata di ``create`` ed ``edit``."""
    result = obj if isinstance(obj, CatalogWriteResult) else None
    catalog = result.catalog if result is not None else None
    parent = result.parent_catalog if result is not None else None
    return {
        "catalog_id": result.catalog_id if result is not None else None,
        "name": catalog.name if catalog is not None else None,
        "parent_catalog_id": parent.id if parent is not None else None,
        "next_occ_token": result.next_occ_token if result is not None else None,
    }


def _entry_row(obj: object) -> dict[str, object]:
    """Tabella curata di ``create-entry`` ed ``edit-entry``."""
    result = obj if isinstance(obj, CatalogEntryWriteResult) else None
    entry = result.entry if result is not None else None
    return {
        "entry_id": result.entry_id if result is not None else None,
        "catalog_id": result.catalog_id if result is not None else None,
        "label": entry.label if entry is not None else None,
        "external_id": entry.external_id if entry is not None else None,
        "next_occ_token": result.next_occ_token if result is not None else None,
    }


def _render(  # noqa: PLR0913
    state: CliState,
    output: str | None,
    result: object,
    row: Any,
    *,
    title: str,
    full: bool,
    fields: str | None,
    export: Any,
    export_format: str | None,
    console: Any,
) -> None:
    render_output(
        resolve_output(state, output),
        [result],
        row,
        full=full,
        fields=fields,
        console=console,
        title=title,
        export_path=export,
        export_format=export_format,
        quiet=state.quiet,
        single_command=True,
    )


@app.command("create")
def catalogs_create(  # noqa: PLR0913
    ctx: typer.Context,
    name: NameOption = None,
    parent: ParentOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create a catalog (requires admin permissions).

    Fields come from flags or from --json (file or '-' for stdin); flags override the keys of
    the JSON body, and --name LANG=TEXT updates the name map one language at a time.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    name_map = parse_lang_map(name, option="--name")
    merged = merge_body(load_json_body(json_body, CreateEditCatalogRequestDTO), parent_id=parent)
    merge_lang_map(merged, "name", name_map)
    req = validate_body(merged, CreateEditCatalogRequestDTO)
    try:
        with build_client(state) as client:
            result = client.catalogs.create_raw(req)
        _render(
            state,
            output,
            result,
            _catalog_row,
            title=f"Catalog {result.catalog_id} created",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("create-entry")
def catalogs_create_entry(  # noqa: PLR0913
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    label: LabelOption = None,
    parent_entry: ParentEntryOption = None,
    external_id: ExternalIdOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Create an entry in a catalog (requires admin permissions).

    Fields come from flags or from --json; flags override the keys of the JSON body, and
    --label LANG=TEXT updates the label map one language at a time.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    label_map = parse_lang_map(label, option="--label")
    merged = merge_body(
        load_json_body(json_body, CreateEditCatalogEntryRequestDTO),
        parent_ids=parent_entry,
        external_id=external_id,
    )
    merge_lang_map(merged, "label", label_map)
    req = validate_body(merged, CreateEditCatalogEntryRequestDTO)
    try:
        with build_client(state) as client:
            result = client.catalogs.create_entry_raw(catalog_id, req)
        _render(
            state,
            output,
            result,
            _entry_row,
            title=f"Entry {result.entry_id} of catalog {catalog_id} created",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
