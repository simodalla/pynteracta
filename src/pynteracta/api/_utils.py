# SPDX-License-Identifier: Apache-2.0
"""Shared helpers for building request DTOs from snake_case kwargs."""

from __future__ import annotations

from typing import Any


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


def build_query_params(**kwargs: Any) -> dict[str, Any]:
    """Build query params from snake_case kwargs, omitting ``None`` values."""
    params: dict[str, Any] = {}
    for key, value in kwargs.items():
        if value is not None:
            params[snake_to_camel(key)] = value
    return params
