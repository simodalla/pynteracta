# SPDX-License-Identifier: Apache-2.0
"""Test del modulo ``keychain``: portachiavi accettati e rifiutati, extra assente (spec 10)."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

import pytest
from google_fakes import CLIENT_ID, CLIENT_SECRET, MemoryKeychain
from keyring.backends import chainer, fail, null
from keyring.errors import PasswordSetError
from typer.testing import CliRunner

from pynteracta import keychain
from pynteracta.auth import build_cache_key
from pynteracta.cli import app
from pynteracta.exceptions import ConfigurationError

_PYPROJECT = Path(__file__).resolve().parents[2] / "pyproject.toml"


def _backend_of_module(module: str) -> Any:
    """Un backend finto il cui tipo dichiara il modulo ``module``."""
    cls = type("Keyring", (), {"__module__": module})
    return cls()


def _use_backend(monkeypatch: pytest.MonkeyPatch, backend: Any) -> None:
    import keyring  # noqa: PLC0415

    monkeypatch.setattr(keyring, "get_keyring", lambda: backend)


class TestOpenKeychain:
    # criterio: 10-C05
    def test_missing_keyring_names_the_extra(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setitem(sys.modules, "keyring", None)
        with pytest.raises(ConfigurationError, match=r"pynteracta\[google\]"):
            keychain.open_keychain()

    # criterio: 10-C06
    @pytest.mark.parametrize(
        "backend",
        [fail.Keyring(), null.Keyring(), _backend_of_module("keyrings.alt.file")],
        ids=["fail", "null", "plaintext-file"],
    )
    def test_rejected_backends_point_to_static_token(
        self, monkeypatch: pytest.MonkeyPatch, backend: Any
    ) -> None:
        _use_backend(monkeypatch, backend)
        with pytest.raises(ConfigurationError, match="static Google token"):
            keychain.open_keychain()

    # criterio: 10-C06
    @pytest.mark.parametrize(
        "module",
        [
            "keyring.backends.macOS",
            "keyring.backends.Windows",
            "keyring.backends.SecretService",
            "keyring.backends.libsecret",
            "keyring.backends.kwallet",
        ],
    )
    def test_accepted_backends(self, monkeypatch: pytest.MonkeyPatch, module: str) -> None:
        _use_backend(monkeypatch, _backend_of_module(module))
        assert isinstance(keychain.open_keychain(), keychain.Keychain)

    # criterio: 10-C06
    def test_homogeneous_chainer_accepted(self, monkeypatch: pytest.MonkeyPatch) -> None:
        backend = chainer.ChainerBackend.__new__(chainer.ChainerBackend)
        monkeypatch.setattr(
            chainer.ChainerBackend,
            "backends",
            [_backend_of_module("keyring.backends.SecretService")],
        )
        _use_backend(monkeypatch, backend)
        assert isinstance(keychain.open_keychain(), keychain.Keychain)

    # criterio: 10-C06
    @pytest.mark.parametrize(
        "inner",
        [
            [_backend_of_module("keyring.backends.SecretService"), null.Keyring()],
            [],
        ],
        ids=["mixed", "empty"],
    )
    def test_mixed_or_empty_chainer_rejected(
        self, monkeypatch: pytest.MonkeyPatch, inner: list[Any]
    ) -> None:
        backend = chainer.ChainerBackend.__new__(chainer.ChainerBackend)
        monkeypatch.setattr(chainer.ChainerBackend, "backends", inner)
        _use_backend(monkeypatch, backend)
        with pytest.raises(ConfigurationError, match="static Google token"):
            keychain.open_keychain()


class TestKeychainEntries:
    def test_get_set_delete(self) -> None:
        kc = MemoryKeychain()
        assert kc.get("x") is None
        kc.set("x", "v")
        assert kc.get("x") == "v"
        kc.delete("x")
        assert kc.get("x") is None
        kc.delete("x")  # voce assente: nessun errore

    def test_entry_names(self) -> None:
        api_base = "https://api.example.com/portal/api/external/v2"
        assert keychain.session_entry(api_base, "prod") == (
            f"google-session:{build_cache_key(api_base, 'prod')}"
        )
        assert keychain.client_secret_entry(CLIENT_ID) == f"google-client-secret:{CLIENT_ID}"

    def test_service_name(self) -> None:
        kc = MemoryKeychain()
        kc.set("x", "v")
        assert ("pynteracta", "x") in kc._memory.store

    # criterio: 10-C06
    def test_keyring_error_becomes_configuration_error_without_value(self) -> None:
        class _Broken:
            def get_password(self, service: str, username: str) -> str | None:
                raise PasswordSetError(CLIENT_SECRET)

            def set_password(self, service: str, username: str, password: str) -> None:
                raise PasswordSetError(password)

            def delete_password(self, service: str, username: str) -> None:
                raise RuntimeError(CLIENT_SECRET)

        kc = keychain.Keychain(_Broken())
        for call in (
            lambda: kc.set("x", CLIENT_SECRET),
            lambda: kc.get("x"),
            lambda: kc.delete("x"),
        ):
            with pytest.raises(ConfigurationError) as info:
                call()
            assert CLIENT_SECRET not in str(info.value)
            assert CLIENT_SECRET not in repr(info.value)
            assert info.value.__cause__ is None
            assert info.value.__suppress_context__


class TestPackaging:
    # criterio: 10-C37
    def test_keyring_only_in_google_extra(self) -> None:
        project = tomllib.loads(_PYPROJECT.read_text(encoding="utf-8"))["project"]
        assert not any(dep.startswith("keyring") for dep in project["dependencies"])
        assert any(dep.startswith("keyring") for dep in project["optional-dependencies"]["google"])

    # criterio: 10-C37
    def test_imports_without_keyring(self) -> None:
        code = (
            "import sys; sys.modules['keyring'] = None; "
            "import pynteracta, pynteracta.client, pynteracta.cli, pynteracta.keychain"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=False
        )
        assert result.returncode == 0, result.stderr

    # criterio: 10-C37
    def test_service_account_whoami_without_keyring(
        self, monkeypatch: pytest.MonkeyPatch, respx_mock: Any
    ) -> None:
        from api_helpers import load_payload, mock_json  # noqa: PLC0415

        monkeypatch.setitem(sys.modules, "keyring", None)
        mock_json(
            "GET", "core/auth/current-user-data", load_payload("current_user_data_response.json")
        )
        result = CliRunner().invoke(
            app, ["auth", "whoami"], env={"PYNTERACTA_BASE_URL": "https://api.example.com"}
        )
        assert result.exit_code == 0, result.output
