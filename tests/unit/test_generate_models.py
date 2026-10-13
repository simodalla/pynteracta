# SPDX-License-Identifier: Apache-2.0
"""Test dello script di rigenerazione dei modelli: ordine stabile delle definizioni (spec 09)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest
import respx

_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "generate_models.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("generate_models_under_test", _SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def script() -> ModuleType:
    return _load_script()


def _swagger(*names: str, note: str = "") -> dict:  # type: ignore[type-arg]
    return {
        "swagger": "2.0",
        "info": {"version": "CERT", "title": "Test è"},
        "paths": {"/a": {"get": {}}},
        "definitions": {name: {"type": "object", "description": f"{name}{note}"} for name in names},
    }


class TestStableDefinitionsOrder:
    # criterio: 09-C18
    def test_previous_order_kept_and_new_appended(self, script: ModuleType) -> None:
        previous = _swagger("B", "A", "C")
        new = _swagger("C", "D", "A", "B", note="-new")
        result = script.stable_definitions_order(new, previous)
        assert list(result["definitions"]) == ["B", "A", "C", "D"]
        assert result["definitions"] == new["definitions"]
        assert result["paths"] == new["paths"]
        assert result["info"] == new["info"]

    # criterio: 09-C18
    def test_removed_definitions_are_dropped(self, script: ModuleType) -> None:
        result = script.stable_definitions_order(_swagger("C", "A"), _swagger("A", "B", "C"))
        assert list(result["definitions"]) == ["A", "C"]

    # criterio: 09-C18
    def test_without_previous_order_is_unchanged(self, script: ModuleType) -> None:
        new = _swagger("C", "A", "B")
        result = script.stable_definitions_order(new, None)
        assert list(result["definitions"]) == ["C", "A", "B"]


class TestDownloadSwagger:
    # criterio: 09-C18
    @respx.mock
    def test_written_in_previous_order_and_compact_format(
        self, script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        snapshot = tmp_path / "swagger.json"
        snapshot.write_text(json.dumps(_swagger("B", "A")), encoding="utf-8")
        monkeypatch.setattr(script, "SWAGGER_SNAPSHOT", snapshot)
        live = _swagger("A", "C", "B")
        respx.get(script.SWAGGER_URL).mock(return_value=httpx.Response(200, json=live))
        script.download_swagger()
        written = snapshot.read_bytes()
        expected = script.stable_definitions_order(live, _swagger("B", "A"))
        assert written == json.dumps(expected, separators=(",", ":"), ensure_ascii=False).encode()
        assert list(json.loads(written)["definitions"]) == ["B", "A", "C"]

    # criterio: 09-C18
    @respx.mock
    def test_first_download_keeps_received_order(
        self, script: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        snapshot = tmp_path / "fixtures" / "swagger.json"
        monkeypatch.setattr(script, "SWAGGER_SNAPSHOT", snapshot)
        respx.get(script.SWAGGER_URL).mock(
            return_value=httpx.Response(200, json=_swagger("C", "A"))
        )
        script.download_swagger()
        assert list(json.loads(snapshot.read_bytes())["definitions"]) == ["C", "A"]
