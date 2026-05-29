# SPDX-License-Identifier: Apache-2.0
from pathlib import Path

import pytest

from pynteracta.config import Config, load_config, resolve_profile

_MINIMAL_TOML = """\
[profiles.dev]
base_url = "https://interacta.example.it"
"""

_FULL_TOML = """\
current_profile = "dev"

[profiles.dev]
base_url        = "https://interacta.example.it"
base_path       = "/myportal"
api_version     = 3
timeout_seconds = 60.0
log_level       = "DEBUG"
"""

_DEFAULT_BASE_PATH = "/portal"
_DEFAULT_API_VERSION = 2
_DEFAULT_TIMEOUT = 30.0
_DEFAULT_LOG_LEVEL = "INFO"
_DEFAULT_TOKEN_CACHE = "file"

_FULL_API_VERSION = 3
_FULL_TIMEOUT = 60.0
_FULL_TIMEOUT_ENV = 99.0
_FULL_TIMEOUT_OVERRIDE = 5.0


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "config.toml"
    p.write_text(content, encoding="utf-8")
    return p


class TestLoadConfig:
    def test_missing_file_returns_empty(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path / "nonexistent.toml")
        assert isinstance(cfg, Config)
        assert cfg.profiles == {}
        assert cfg.current_profile == "default"

    def test_loads_profiles(self, tmp_path: Path) -> None:
        cfg = load_config(_write(tmp_path, _MINIMAL_TOML))
        assert "dev" in cfg.profiles

    def test_current_profile_default(self, tmp_path: Path) -> None:
        cfg = load_config(_write(tmp_path, _MINIMAL_TOML))
        assert cfg.current_profile == "default"

    def test_current_profile_explicit(self, tmp_path: Path) -> None:
        cfg = load_config(_write(tmp_path, _FULL_TOML))
        assert cfg.current_profile == "dev"


class TestProfileDefaults:
    def test_defaults_applied(self, tmp_path: Path) -> None:
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert profile.base_path == _DEFAULT_BASE_PATH
        assert profile.api_version == _DEFAULT_API_VERSION
        assert profile.timeout_seconds == _DEFAULT_TIMEOUT
        assert profile.log_level == _DEFAULT_LOG_LEVEL
        assert profile.token_cache == _DEFAULT_TOKEN_CACHE
        assert profile.service_account_key is None
        assert profile.token_cache_dir is None

    def test_file_values_override_defaults(self, tmp_path: Path) -> None:
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.base_path == "/myportal"
        assert profile.api_version == _FULL_API_VERSION
        assert profile.timeout_seconds == _FULL_TIMEOUT
        assert profile.log_level == "DEBUG"


class TestEnvPrecedence:
    def test_env_base_url_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_BASE_URL", "https://override.example.it")
        profile = resolve_profile("dev", _write(tmp_path, _MINIMAL_TOML))
        assert str(profile.base_url).rstrip("/") == "https://override.example.it"

    def test_env_base_path_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_BASE_PATH", "/env-path")
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.base_path == "/env-path"

    def test_env_timeout_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_TIMEOUT", "99.0")
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.timeout_seconds == _FULL_TIMEOUT_ENV

    def test_env_log_level_overrides_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("PYNTERACTA_LOG_LEVEL", "WARNING")
        profile = resolve_profile("dev", _write(tmp_path, _FULL_TOML))
        assert profile.log_level == "WARNING"


class TestExplicitOverrides:
    def test_override_wins_over_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYNTERACTA_BASE_PATH", "/env-path")
        profile = resolve_profile(
            "dev",
            _write(tmp_path, _MINIMAL_TOML),
            overrides={"base_path": "/cli-path"},
        )
        assert profile.base_path == "/cli-path"

    def test_override_wins_over_file(self, tmp_path: Path) -> None:
        profile = resolve_profile(
            "dev",
            _write(tmp_path, _FULL_TOML),
            overrides={"timeout_seconds": _FULL_TIMEOUT_OVERRIDE},
        )
        assert profile.timeout_seconds == _FULL_TIMEOUT_OVERRIDE
