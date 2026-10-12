# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for building request DTOs from snake_case kwargs."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


def snake_to_camel(name: str) -> str:
    """Convert ``snake_case`` to ``camelCase``."""
    parts = name.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


def build_paginated_body(
    *,
    page_token: str | None = None,
    page_size: int | None = None,
    calculate_total_items_count: bool | None = None,
    **filters: Any,
) -> dict[str, Any]:
    """Build a request-body dict with pagination fields and camelCase filters."""
    data: dict[str, Any] = {}
    if page_token is not None:
        data["pageToken"] = page_token
    if page_size is not None:
        data["pageSize"] = page_size
    if calculate_total_items_count is not None:
        data["calculateTotalItemsCount"] = calculate_total_items_count
    for key, value in filters.items():
        if value is not None:
            data[snake_to_camel(key)] = value
    return data


def to_epoch_millis(value: int | float | str | datetime | None) -> int | None:
    """Coerce *value* to epoch-milliseconds integer.

    Accepts:
    - ``int`` / ``float`` — returned as ``int``, assumed already epoch-millis.
    - :class:`datetime` — converted via UTC if naive.
    - ISO-8601 ``str`` — parsed then converted.
    - Integer-literal ``str`` (e.g. ``"1735689600000"`` from a CLI flag) — treated as epoch-millis.
    - ``None`` — returned as ``None``.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value.strip())
    dt = value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def build_query_params(**kwargs: Any) -> dict[str, Any]:
    """Build query params from snake_case kwargs, omitting ``None`` values."""
    params: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is not None:
            params[snake_to_camel(key)] = value
    return params


def zoned_datetime_input(value: datetime) -> dict[str, str]:
    """Traduce un ``datetime`` con fuso nella coppia ``{datetime, timezone}`` delle scritture.

    Con un fuso IANA (``ZoneInfo``) invia l'ora locale e il nome del fuso; con un offset fisso,
    che non ha un nome IANA, converte in UTC e invia ``"UTC"``. Un ``datetime`` senza fuso è
    rifiutato prima di qualunque chiamata al server.
    """
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "expiration must be a timezone-aware datetime"
        raise ValueError(msg)
    key = getattr(value.tzinfo, "key", None)
    if key is None:
        value = value.astimezone(UTC)
        key = "UTC"
    return {"datetime": value.replace(tzinfo=None).isoformat(timespec="seconds"), "timezone": key}


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = f"{name} must be a timezone-aware datetime"
        raise ValueError(msg)


def event_datetime_block(start_at: datetime | None, end_at: datetime | None) -> dict[str, Any]:
    """Traduce inizio e fine di un evento nelle chiavi ``startAt``, ``endAt`` e ``timezone``.

    Il fuso dell'evento è quello di ``start_at`` (di ``end_at`` se ``start_at`` manca): con un
    fuso IANA (``ZoneInfo``) si invia il suo nome, con un offset fisso, che non ha un nome IANA,
    si converte in UTC e si invia ``"UTC"``. L'altra data è convertita in quel fuso. Ogni data
    viaggia come ``{"localDatetime": ...}`` senza offset. Compaiono solo le chiavi delle date
    passate; senza date il risultato è ``{}``.

    Raises:
        ValueError: se una delle date passate non ha fuso, prima di qualunque chiamata.
    """
    if start_at is not None:
        _require_aware(start_at, "start_at")
    if end_at is not None:
        _require_aware(end_at, "end_at")
    reference = start_at if start_at is not None else end_at
    if reference is None:
        return {}
    key = getattr(reference.tzinfo, "key", None)
    zone: tzinfo = (reference.tzinfo or UTC) if key is not None else UTC
    if key is None:
        key = "UTC"
    block: dict[str, Any] = {}
    if start_at is not None:
        block["startAt"] = {"localDatetime": _local_iso(start_at, zone)}
    if end_at is not None:
        block["endAt"] = {"localDatetime": _local_iso(end_at, zone)}
    block["timezone"] = key
    return block


def _local_iso(value: datetime, zone: tzinfo) -> str:
    return value.astimezone(zone).replace(tzinfo=None).isoformat(timespec="seconds")


@runtime_checkable
class WriteInput(Protocol):
    """Un oggetto che sa come comparire nel corpo di una scrittura (spec 04).

    :func:`build_write_body` lo sostituisce con il dict di :meth:`as_write_input`, anche dentro
    le liste: per esempio un :class:`~pynteracta.models.facade.attachments.UploadedAttachment`
    negli allegati di un post.
    """

    def as_write_input(self) -> dict[str, Any]: ...


def _dump_value(value: Any) -> Any:
    if isinstance(value, WriteInput):
        return value.as_write_input()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", exclude_none=True)
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    return value


def build_write_body(**kwargs: Any) -> dict[str, Any]:
    """Costruisce il corpo di una scrittura dai kwargs: camelCase, solo i campi non ``None``.

    I modelli pydantic (anche dentro le liste) sono dumpati senza i campi ``None``; gli oggetti
    :class:`WriteInput` diventano il loro ``as_write_input()``; dict e valori semplici passano
    così come sono.
    """
    body: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is not None:
            body[snake_to_camel(key)] = _dump_value(value)
    return body
