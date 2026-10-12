# SPDX-License-Identifier: Apache-2.0
"""Rivalidazione degli stub ``RootModel[Any]`` dei modelli generati nelle varianti tipizzate.

Condivisa dalle façade di scrittura dei post (spec 03) e dei post evento (spec 08).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


def typed[M: BaseModel](stub: object, model: type[M]) -> M | None:
    """Rivalida uno stub ``RootModel`` (o un dict) nel modello tipizzato; ``None`` se vuoto."""
    root = getattr(stub, "root", stub)
    if isinstance(root, dict):
        return model.model_validate(root)
    return None


def typed_list[M: BaseModel](stubs: list[Any] | None, model: type[M]) -> list[M]:
    """Rivalida una lista di stub; gli elementi non oggetto si scartano."""
    items = (typed(item, model) for item in stubs or [])
    return [item for item in items if item is not None]
