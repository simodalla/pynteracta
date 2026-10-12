# SPDX-License-Identifier: Apache-2.0
"""Comandi di scrittura di cataloghi e voci (spec 06), registrati sul gruppo ``catalogs``.

I testi della CLI (help, prompt, messaggi) sono in inglese, come il resto della CLI. Ogni comando
invia una sola richiesta di scrittura e non riprova mai: un ``409`` esce con il codice ``9``. Le
mappe per lingua (``--name``, ``--label``) si passano come ``LANG=TEXT`` ripetibili e si uniscono
chiave per chiave alla mappa di ``--json`` o del form letto.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

import typer

from pynteracta.cli._common import (
    EXIT_GENERIC,
    EXIT_SUCCESS,
    CliState,
    ExportFormatOption,
    ExportOption,
    FieldsOption,
    FullOption,
    OutputOption,
    build_client,
    confirm_destructive,
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
    OccTokenOption,
    merge_body,
    merge_lang_map,
    parse_lang_map,
    validate_body,
)
from pynteracta.cli.catalogs import app
from pynteracta.exceptions import InteractaError
from pynteracta.models.facade.admin_manage import CatalogEntryForEdit, CatalogForEdit
from pynteracta.models.facade.catalogs import (
    CatalogEntry,
    CatalogEntryWriteResult,
    CatalogWriteResult,
)
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


def _catalog_edit_base(form: CatalogForEdit) -> dict[str, Any]:
    """Corpo di ``edit`` ricavato dal form letto (06-C11): nome e parent si rimandano.

    Le chiavi assenti nel form non si inventano; ``deleted`` non si rimanda mai: si cambia con
    ``delete`` e ``restore``.
    """
    base: dict[str, Any] = {"name": form.name, "parentId": form.parent_catalog_id}
    return {key: value for key, value in base.items() if value is not None}


def _entry_edit_base(form: CatalogEntryForEdit) -> dict[str, Any]:
    """Corpo di ``edit-entry`` ricavato dal form letto (06-C12).

    ``parentIds`` sono gli id dei ``parents`` letti; la chiave manca se il form non ha
    ``parents``. ``deleted`` non si rimanda mai.
    """
    base: dict[str, Any] = {"label": form.label, "externalId": form.external_id}
    body = {key: value for key, value in base.items() if value is not None}
    if form.raw.parents is not None:
        parents = [CatalogEntry.from_stub(p) for p in form.raw.parents]
        body["parentIds"] = [p.id for p in parents if p.id is not None]
    return body


def _display_name(mapping: dict[str, str] | None) -> str:
    """Il nome da mostrare nel prompt: la lingua ``it`` se c'è, altrimenti la prima, o ``""``."""
    if not mapping:
        return ""
    return mapping.get("it", next(iter(mapping.values())))


YesOption = Annotated[bool, typer.Option("--yes", "-y", help="Do not ask for confirmation.")]


def _print_deleted(  # noqa: PLR0913
    state: CliState,
    console: Any,
    output: str | None,
    *,
    catalog_id: int,
    entry_id: int | None,
    deleted: bool,
) -> None:
    """Esito di ``delete``/``restore``: riga di testo o JSON con gli id e il flag."""
    if resolve_output(state, output) == "json":
        payload: dict[str, Any] = {"catalog_id": catalog_id}
        if entry_id is not None:
            payload["entry_id"] = entry_id
        payload["deleted"] = deleted
        typer.echo(json.dumps(payload))
        return
    if state.quiet:
        return
    verb = "deleted" if deleted else "restored"
    if entry_id is None:
        console.print(f"Catalog {catalog_id} {verb}")
    else:
        console.print(f"Entry {entry_id} of catalog {catalog_id} {verb}")


def _require_token(resource: str, occ_token: int | None, read_token: int | None) -> int:
    """Il token da inviare: ``--occ-token`` se dato, altrimenti quello letto; nessuno → exit 1."""
    token = occ_token if occ_token is not None else read_token
    if token is None:
        typer.echo(
            f"{resource} has no occToken in the server response: pass --occ-token explicitly.",
            err=True,
        )
        raise typer.Exit(EXIT_GENERIC)
    return token


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


@app.command("edit")
def catalogs_edit(  # noqa: PLR0913
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    occ_token: OccTokenOption = None,
    name: NameOption = None,
    parent: ParentOption = None,
    json_body: JsonBodyOption = None,
    output: OutputOption = None,
    full: FullOption = False,
    fields: FieldsOption = None,
    export: ExportOption = None,
    export_format: ExportFormatOption = None,
) -> None:
    """Edit a catalog, keeping what you do not mention.

    The catalog's edit form is read first and its name map and parent are sent back unless a
    flag or --json overrides them (flags win over --json, --json over the form as read);
    --name LANG=TEXT updates one language and keeps the others. The deleted flag is never sent:
    use 'catalogs delete' and 'catalogs restore'. The concurrency token is the one just read, or
    --occ-token. A 409 exits with code 9 and never retries.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, CreateEditCatalogRequestDTO)
    name_map = parse_lang_map(name, option="--name")
    resource = f"Catalog {catalog_id}"
    try:
        with build_client(state) as client:
            form = client.catalogs.get_for_edit(catalog_id)
            token = _require_token(resource, occ_token, form.occ_token)
            merged = merge_body({**_catalog_edit_base(form), **json_part}, parent_id=parent)
            merge_lang_map(merged, "name", name_map)
            merged["occToken"] = token
            req = validate_body(merged, CreateEditCatalogRequestDTO)
            result = client.catalogs.edit_raw(catalog_id, req)
        _render(
            state,
            output,
            result,
            _catalog_row,
            title=f"Catalog {catalog_id} updated",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=resource) from exc


@app.command("edit-entry")
def catalogs_edit_entry(  # noqa: PLR0913
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    entry_id: Annotated[int, typer.Argument(help="Entry ID.")],
    occ_token: OccTokenOption = None,
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
    """Edit a catalog entry, keeping what you do not mention.

    The entry's edit form is read first and its label map, parent entries and external id are
    sent back unless a flag or --json overrides them; --label LANG=TEXT updates one language,
    --parent-entry replaces the whole parent list. The deleted flag is never sent: use
    'catalogs delete-entry' and 'catalogs restore-entry'. A 409 exits with code 9.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    validate_full_fields(full, fields)
    validate_export_options(export, export_format)
    json_part = load_json_body(json_body, CreateEditCatalogEntryRequestDTO)
    label_map = parse_lang_map(label, option="--label")
    resource = f"Entry {entry_id} of catalog {catalog_id}"
    try:
        with build_client(state) as client:
            form = client.catalogs.get_entry_for_edit(catalog_id, entry_id)
            token = _require_token(resource, occ_token, form.occ_token)
            merged = merge_body(
                {**_entry_edit_base(form), **json_part},
                parent_ids=parent_entry,
                external_id=external_id,
            )
            merge_lang_map(merged, "label", label_map)
            merged["occToken"] = token
            req = validate_body(merged, CreateEditCatalogEntryRequestDTO)
            result = client.catalogs.edit_entry_raw(catalog_id, entry_id, req)
        _render(
            state,
            output,
            result,
            _entry_row,
            title=f"Entry {entry_id} of catalog {catalog_id} updated",
            full=full,
            fields=fields,
            export=export,
            export_format=export_format,
            console=console,
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console, resource=resource) from exc


@app.command("delete")
def catalogs_delete(
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    yes: YesOption = False,
    output: OutputOption = None,
) -> None:
    """Delete a catalog (logical deletion: 'catalogs restore' brings it back).

    The catalog stays on the tenant with deleted=true. Its edit form is read first and its id
    and name shown in a confirmation prompt; without an interactive terminal --yes is required.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            form = client.catalogs.get_for_edit(catalog_id)
            prompt = f'Delete catalog {catalog_id} "{_display_name(form.name)}"?'
            if not confirm_destructive(prompt, yes=yes):
                raise typer.Exit(EXIT_SUCCESS)
            client.catalogs.set_deleted(catalog_id, True)
        _print_deleted(state, console, output, catalog_id=catalog_id, entry_id=None, deleted=True)
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("restore")
def catalogs_restore(
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    output: OutputOption = None,
) -> None:
    """Restore a deleted catalog (sets deleted=false; no confirmation)."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            client.catalogs.set_deleted(catalog_id, False)
        _print_deleted(state, console, output, catalog_id=catalog_id, entry_id=None, deleted=False)
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("delete-entry")
def catalogs_delete_entry(
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    entry_id: Annotated[int, typer.Argument(help="Entry ID.")],
    yes: YesOption = False,
    output: OutputOption = None,
) -> None:
    """Delete a catalog entry (logical deletion: 'catalogs restore-entry' brings it back).

    The entry stays on the tenant with deleted=true. Its edit form is read first and its id and
    label shown in a confirmation prompt; without an interactive terminal --yes is required.
    """
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            form = client.catalogs.get_entry_for_edit(catalog_id, entry_id)
            label = _display_name(form.label)
            prompt = f'Delete entry {entry_id} "{label}" of catalog {catalog_id}?'
            if not confirm_destructive(prompt, yes=yes):
                raise typer.Exit(EXIT_SUCCESS)
            client.catalogs.set_entry_deleted(catalog_id, entry_id, True)
        _print_deleted(
            state, console, output, catalog_id=catalog_id, entry_id=entry_id, deleted=True
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc


@app.command("restore-entry")
def catalogs_restore_entry(
    ctx: typer.Context,
    catalog_id: Annotated[int, typer.Argument(help="Catalog ID.")],
    entry_id: Annotated[int, typer.Argument(help="Entry ID.")],
    output: OutputOption = None,
) -> None:
    """Restore a deleted catalog entry (sets deleted=false; no confirmation)."""
    state: CliState = ctx.obj
    console = make_console(state)
    try:
        with build_client(state) as client:
            client.catalogs.set_entry_deleted(catalog_id, entry_id, False)
        _print_deleted(
            state, console, output, catalog_id=catalog_id, entry_id=entry_id, deleted=False
        )
        raise typer.Exit(EXIT_SUCCESS)
    except InteractaError as exc:
        raise handle_error(exc, console=console) from exc
