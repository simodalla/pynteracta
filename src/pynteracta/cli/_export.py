# SPDX-License-Identifier: Apache-2.0
"""Export helpers: format inference, serialization, and file writing for --export."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import typer

from pynteracta.cli._common import EXIT_CONFIG, _compact_json

EXPORT_FORMATS = ("csv", "json", "yaml", "parquet")

_EXT_MAP: dict[str, str] = {
    ".csv": "csv",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".parquet": "parquet",
}


def infer_export_format(path: Path, override: str | None) -> str:
    """Return the export format string, validated against EXPORT_FORMATS.

    Priority: explicit override > file extension.
    Exits with EXIT_CONFIG if the format cannot be determined or is unknown.
    """
    if override is not None:
        if override not in EXPORT_FORMATS:
            typer.echo(
                f"Unknown --export-format '{override}'. "
                f"Supported formats: {', '.join(EXPORT_FORMATS)}",
                err=True,
            )
            raise typer.Exit(EXIT_CONFIG)
        return override

    ext = path.suffix.lower()
    fmt = _EXT_MAP.get(ext)
    if fmt is None:
        typer.echo(
            f"Cannot infer export format from extension '{ext or '(none)'}'. "
            f"Use --export-format to specify one of: {', '.join(EXPORT_FORMATS)}",
            err=True,
        )
        raise typer.Exit(EXIT_CONFIG)
    return fmt


def _check_parquet_available() -> None:
    try:
        import pyarrow  # noqa: F401, PLC0415
    except ImportError:
        typer.echo(
            "Parquet export requires pyarrow. Install it with: pip install pynteracta[parquet]",
            err=True,
        )
        raise typer.Exit(EXIT_CONFIG) from None


def _ordered_union_columns(records: list[dict[str, Any]]) -> list[str]:
    """Return the ordered union of all keys across records (first-seen order)."""
    seen: dict[str, None] = {}
    for rec in records:
        for key in rec:
            seen[key] = None
    return list(seen)


def _write_csv(records: list[dict[str, Any]], path: Path) -> None:
    columns = _ordered_union_columns(records)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for rec in records:
            row = {col: "" for col in columns}
            for k, v in rec.items():
                if isinstance(v, (dict, list)):
                    row[k] = _compact_json(v)
                elif v is None:
                    row[k] = ""
                else:
                    row[k] = v
            writer.writerow(row)


def _write_json(records: list[dict[str, Any]], path: Path, *, single: bool) -> None:
    data: Any = records[0] if single and len(records) == 1 else records
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, default=str, indent=2)
        f.write("\n")


def _write_yaml(records: list[dict[str, Any]], path: Path, *, single: bool) -> None:
    from pynteracta.cli._common import _check_yaml_available  # noqa: PLC0415

    _check_yaml_available()
    from ruamel.yaml import YAML  # noqa: PLC0415

    data: Any = records[0] if single and len(records) == 1 else records
    yml = YAML()
    with path.open("w", encoding="utf-8") as f:
        yml.dump(data, f)


def _write_parquet(records: list[dict[str, Any]], path: Path) -> None:
    _check_parquet_available()
    import pyarrow as pa  # noqa: PLC0415
    import pyarrow.parquet as pq  # noqa: PLC0415

    columns = _ordered_union_columns(records)
    col_data: dict[str, list[Any]] = {col: [] for col in columns}
    for rec in records:
        for col in columns:
            v = rec.get(col)
            if isinstance(v, (dict, list)):
                col_data[col].append(_compact_json(v))
            else:
                col_data[col].append(v)

    arrays = []
    fields = []
    for col in columns:
        values = col_data[col]
        # Convert non-None values to strings if any are dicts/lists (already done above)
        # Let pyarrow infer the type; use string for mixed/nested columns
        try:
            arr = pa.array(values)
        except (pa.ArrowInvalid, pa.ArrowTypeError):
            arr = pa.array([str(v) if v is not None else None for v in values], type=pa.string())
        arrays.append(arr)
        fields.append(pa.field(col, arr.type))

    table = pa.table({col: arr for col, arr in zip(columns, arrays, strict=True)})
    pq.write_table(table, path)  # type: ignore[no-untyped-call]


def export_records(
    records: list[dict[str, Any]],
    path: Path,
    fmt: str,
    *,
    single: bool = False,
) -> int:
    """Write *records* to *path* in *fmt* format; create parent dirs if needed.

    Returns the number of records written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "csv":
        _write_csv(records, path)
    elif fmt == "json":
        _write_json(records, path, single=single)
    elif fmt == "yaml":
        _write_yaml(records, path, single=single)
    elif fmt == "parquet":
        _write_parquet(records, path)
    else:
        typer.echo(f"Unsupported export format: {fmt}", err=True)
        raise typer.Exit(EXIT_CONFIG)
    return len(records)
