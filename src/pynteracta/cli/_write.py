# SPDX-License-Identifier: Apache-2.0
"""Helper condivisi dai comandi di scrittura della CLI (task, post, utenti, gruppi).

Spostati da ``cli/tasks.py`` con la spec 03: data-ora con fuso, unione di ``--json`` e flag,
validazione del corpo contro il DTO, coppie ``ID=VALORE`` ripetibili. Con la spec 04: upload dei
file di ``--attach`` e coppie ``ID=PATH`` di ``--update``. Con la spec 05: le opzioni ``--json`` e
``--occ-token`` condivise e la lettura della password da stdin o da prompt nascosto.
"""

from __future__ import annotations

import pathlib
import sys
from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pydantic
import typer

from pynteracta.api._utils import snake_to_camel, zoned_datetime_input
from pynteracta.cli import _common
from pynteracta.cli._common import EXIT_CONFIG, coerce_filter_value

if TYPE_CHECKING:
    from pynteracta.client import InteractaClient

DEFAULT_TIMEZONE = "Europe/Rome"

AttachOption = Annotated[
    list[pathlib.Path] | None,
    typer.Option(
        "--attach",
        help="File to upload and attach (repeatable). Stops at the first failed upload.",
        exists=True,
        dir_okay=False,
        readable=True,
    ),
]
JsonBodyOption = Annotated[
    str | None,
    typer.Option(
        "--json",
        help=(
            "Full request body as JSON: a file path, or '-' to read stdin. Flags override the "
            "keys they correspond to."
        ),
    ),
]
OccTokenOption = Annotated[
    int | None,
    typer.Option(
        "--occ-token",
        help=(
            "Concurrency token to send instead of the one just read. A 409 (token mismatch) "
            "exits with code 9; nothing is retried."
        ),
    ),
]


def read_password(*, option: str = "--password-stdin") -> str:
    """La password custom di ``users create`` (spec 05), mai da un argomento.

    Con un terminale interattivo la chiede con un prompt nascosto e la conferma; altrimenti
    legge la prima riga dello standard input, senza il fine riga. Una stringa vuota → messaggio
    con il nome di ``option`` ed ``EXIT_CONFIG``, prima di qualunque richiesta.
    """
    if _common._stdin_is_interactive():
        password = str(typer.prompt("Password", hide_input=True, confirmation_prompt=True))
    else:
        password = sys.stdin.readline().rstrip("\r\n")
    if not password:
        typer.echo(f"{option}: no password read from stdin.", err=True)
        raise typer.Exit(EXIT_CONFIG)
    return password


def parse_zoned_datetime(value: str | None, timezone: str, *, option: str) -> dict[str, str] | None:
    """Una data-ora ISO 8601 della CLI → la coppia ``{datetime, timezone}`` del DTO.

    Senza offset il valore è letto nel fuso ``timezone``; con un offset il fuso è ignorato.
    Valore non ISO o fuso sconosciuto → messaggio con il nome di ``option`` ed ``EXIT_CONFIG``.
    """
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        typer.echo(f"{option}: not an ISO 8601 date-time: {value!r}.", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc
    if parsed.tzinfo is None:
        try:
            parsed = parsed.replace(tzinfo=ZoneInfo(timezone))
        except ZoneInfoNotFoundError as exc:
            typer.echo(f"--timezone: unknown IANA time zone {timezone!r}.", err=True)
            raise typer.Exit(EXIT_CONFIG) from exc
    return zoned_datetime_input(parsed)


def merge_body(json_body: dict[str, Any], **flags: Any) -> dict[str, Any]:
    """Unisce il corpo di ``--json`` con i flag: un flag passato sostituisce la sua chiave."""
    merged = dict(json_body)
    for key, value in flags.items():
        if value is not None:
            merged[snake_to_camel(key)] = value
    return merged


def validate_body(merged: dict[str, Any], dto_cls: type[Any]) -> Any:
    """Valida il corpo unito contro il DTO; un corpo non valido → messaggio ed ``EXIT_CONFIG``."""
    try:
        return dto_cls.model_validate(merged)
    except pydantic.ValidationError as exc:
        typer.echo(f"Invalid request body for {dto_cls.__name__}:\n{exc}", err=True)
        raise typer.Exit(EXIT_CONFIG) from exc


def parse_kv_values(values: list[str] | None, *, option: str) -> dict[str, Any]:
    """Coppie ``ID=VALORE`` ripetibili (``--custom-data``, ``--screen-data``) → dict.

    La chiave resta com'è (è l'id di un campo); il valore è tipizzato come in ``--filter``
    (``true``/``false``, interi, altrimenti stringa). Un token senza ``=`` →
    :class:`typer.BadParameter`.
    """
    out: dict[str, Any] = {}
    for item in values or []:
        if "=" not in item:
            raise typer.BadParameter(f"{option} must be ID=VALUE, got: {item!r}")
        key, value = item.split("=", 1)
        out[key.strip()] = coerce_filter_value(value)
    return out


def upload_all(client: InteractaClient, paths: list[pathlib.Path] | None) -> list[dict[str, Any]]:
    """Carica i file di ``--attach`` nell'ordine dato e ne restituisce i riferimenti.

    Ogni riferimento è ``{"name", "contentRef"}``. Il primo errore risale subito: i file dopo non
    sono caricati e il chiamante non invia la scrittura (spec 04).
    """
    return [client.attachments.upload(path).as_write_input() for path in paths or []]


def append_attachments(merged: dict[str, Any], key: str, items: list[dict[str, Any]]) -> None:
    """Accoda ``items`` alla lista ``key`` del corpo (dopo quelli di ``--json``), se ce ne sono."""
    if items:
        merged[key] = [*merged.get(key, []), *items]


def parse_id_path_pairs(values: list[str] | None, *, option: str) -> list[tuple[int, pathlib.Path]]:
    """Coppie ``ID=PATH`` ripetibili (``--update``) → lista di ``(id, percorso)``.

    Si divide al primo ``=``: il percorso può contenerne altri. Un token senza ``=``, con un id
    non intero o con il percorso vuoto → :class:`typer.BadParameter`.
    """
    pairs: list[tuple[int, pathlib.Path]] = []
    for item in values or []:
        key, sep, path = item.partition("=")
        if not sep or not path or not key.strip().isdigit():
            raise typer.BadParameter(f"{option} must be ID=PATH, got: {item!r}")
        pairs.append((int(key), pathlib.Path(path)))
    return pairs
